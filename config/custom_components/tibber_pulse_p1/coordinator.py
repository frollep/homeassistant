"""Coordinator and client for Tibber Pulse P1."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from tibber import Tibber, TibberHome
from tibber.exceptions import InvalidLoginError, RetryableHttpExceptionError
from websockets.exceptions import InvalidStatusCode

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_TOKEN,
    DOMAIN,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)


class TibberPulseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that bridges Tibber GraphQL realtime data into HA."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.home_id: str = entry.data[CONF_HOME_ID]
        self.home_name: str = entry.data.get(CONF_HOME_NAME, "Tibber Home")
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        self.device_name: str = entry.data.get(CONF_DEVICE_NAME, "Tibber Pulse P1")

        self._tibber: Tibber | None = None
        self._home: TibberHome | None = None
        self._started = False
        self._first_data_event: asyncio.Future[None] | None = None
        self._owns_tibber = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.home_id}",
            update_interval=None,
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for entities."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": MANUFACTURER,
        }

    async def _async_setup_rt(self) -> None:
        """Start realtime subscription."""
        if self._started:
            return
        self._started = True
        self._first_data_event = self.hass.loop.create_future()
        session = aiohttp_client.async_get_clientsession(self.hass)
        tibber_shared = self.hass.data.get("tibber")
        if isinstance(tibber_shared, Tibber):
            self._tibber = tibber_shared
        else:
            self._owns_tibber = True
            self._tibber = Tibber(
                access_token=self.entry.data[CONF_TOKEN],
                websession=session,
                user_agent="HomeAssistant tibber_pulse_p1",
            )

        # If we own the Tibber client we must populate homes; otherwise reuse the shared one.
        if self._owns_tibber and self.home_id not in getattr(self._tibber, "_all_home_ids", []):  # type: ignore[attr-defined]
            try:
                await self._tibber.update_info()
            except InvalidLoginError as err:
                raise ConfigEntryAuthFailed from err
            except RetryableHttpExceptionError:
                _LOGGER.warning(
                    "tibber_pulse_p1: rate limited while fetching home info, retrying with cached home id"
                )
                # Fall back to the configured home id; realtime connect does not require the full info payload.
                self._tibber._all_home_ids = list({*self._tibber._all_home_ids, self.home_id})  # type: ignore[attr-defined]
                self._tibber._active_home_ids = list({*self._tibber._active_home_ids, self.home_id})  # type: ignore[attr-defined]
                if not self._tibber.realtime.sub_endpoint:
                    # Default websocket endpoint used by Tibber GraphQL realtime API.
                    self._tibber.realtime.sub_endpoint = (
                        "wss://websocket-api.tibber.com/v1-beta/gql/subscriptions"
                    )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("tibber_pulse_p1: error fetching home info: %s", err)
                raise ConfigEntryNotReady(err) from err

        self._home = self._tibber.get_home(self.home_id)
        if self._home is None:
            raise ConfigEntryNotReady(f"Home {self.home_id} not available")

        await asyncio.gather(
            self._home.update_info(),
            self._home.update_info_and_price_info(),
            return_exceptions=True,
        )

        def _rt_callback(payload: dict[str, Any]) -> None:
            live = payload.get("data", {}).get("liveMeasurement")
            if not live:
                return
            self.hass.add_job(self._handle_live, live)

        # If the built-in Tibber integration already subscribes, piggyback its callback without opening another subscription.
        if not self._owns_tibber:
            for _ in range(120):
                existing_cb = getattr(self._home, "_rt_callback", None)
                if existing_cb:
                    def combined_cb(payload: dict[str, Any]) -> None:
                        try:
                            existing_cb(payload)
                        except Exception:  # noqa: BLE001
                            _LOGGER.exception("tibber_pulse_p1: error in original Tibber callback")
                        _rt_callback(payload)

                    self._home._rt_callback = combined_cb
                    return
                await asyncio.sleep(1)
            raise ConfigEntryNotReady("Waiting for Tibber realtime to start")

        try:
            await self._home.rt_subscribe(_rt_callback)
        except InvalidStatusCode as err:
            _LOGGER.warning(
                "tibber_pulse_p1: websocket connection was rate limited (%s), will retry", err
            )
            raise ConfigEntryNotReady("Tibber websocket rate limited, retrying") from err
        except Exception as err:  # noqa: BLE001
            raise ConfigEntryNotReady(err) from err

    @callback
    def _handle_live(self, live: dict[str, Any]) -> None:
        """Handle incoming live measurement."""
        self.async_set_updated_data(live)
        if self._first_data_event and not self._first_data_event.done():
            self._first_data_event.set_result(None)

    async def _async_update_data(self) -> dict[str, Any]:
        """Wait for first realtime payload."""
        if not self._started:
            await self._async_setup_rt()
        assert self._first_data_event is not None
        try:
            await asyncio.wait_for(self._first_data_event, timeout=90)
        except asyncio.TimeoutError as err:
            raise ConfigEntryNotReady("No data received from Tibber realtime") from err
        return self.data or {}

    async def async_stop(self) -> None:
        """Clean up realtime connection."""
        if self._home:
            self._home.rt_unsubscribe()
        if self._tibber and self._owns_tibber:
            await self._tibber.realtime.disconnect()
            await self._tibber.close_connection()
