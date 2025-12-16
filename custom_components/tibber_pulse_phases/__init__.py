"""Setup for Tibber Pulse Phases integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import websockets
from websockets import WebSocketException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_TOKEN,
    DOMAIN,
    HTTP_URL,
    PLATFORMS,
    SUBSCRIPTION_QUERY,
    WS_URL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up via YAML (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tibber Pulse Phases from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    hub = TibberPulseHub(
        hass=hass,
        session=session,
        token=entry.data[CONF_TOKEN],
        home_id=entry.data[CONF_HOME_ID],
        home_name=entry.data.get(CONF_HOME_NAME, "Tibber Home"),
    )
    await hub.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hub: TibberPulseHub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class TibberPulseHub:
    """Handle Tibber realtime/polling updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        token: str,
        home_id: str,
        home_name: str,
    ) -> None:
        self._hass = hass
        self._session = session
        self._token = token
        self.home_id = home_id
        self.home_name = home_name
        self.last_payload: Dict[str, Any] = {}
        self.available_keys: set[str] = set()
        self.supports_realtime = False
        self._listeners: list[Callable[[], None]] = []
        self._ws_task: Optional[asyncio.Task] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._stopped = False

    async def async_setup(self) -> None:
        """Start realtime or polling."""
        self.supports_realtime = await self._check_realtime()
        if self.supports_realtime:
            self._ws_task = self._hass.loop.create_task(self._run_ws())
        else:
            self._poll_task = self._hass.loop.create_task(self._poll_loop())

    async def async_stop(self) -> None:
        """Stop tasks."""
        self._stopped = True
        if self._ws_task:
            self._ws_task.cancel()
        if self._poll_task:
            self._poll_task.cancel()

    async def _check_realtime(self) -> bool:
        """Check if realtime is enabled for home."""
        query = """
        query HomeFeatures($homeId: ID!) {
          viewer {
            home(id: $homeId) {
              id
              features { realTimeConsumptionEnabled }
            }
          }
        }
        """
        resp = await self._post_graphql(query, {"homeId": self.home_id})
        try:
            return bool(
                resp["data"]["viewer"]["home"]["features"]["realTimeConsumptionEnabled"]
            )
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Could not determine realtime availability, assuming false")
            return False

    async def _post_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query."""
        async with self._session.post(
            HTTP_URL,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _run_ws(self) -> None:
        """Listen for realtime websocket updates."""
        while not self._stopped:
            try:
                async with websockets.connect(
                    WS_URL,
                    extra_headers={"Authorization": f"Bearer {self._token}"},
                    ping_interval=30,
                ) as websocket_client:
                    await websocket_client.send(
                        json.dumps(
                            {"type": "connection_init", "payload": {"token": self._token}}
                        )
                    )
                    await websocket_client.send(
                        json.dumps(
                            {
                                "id": "1",
                                "type": "start",
                                "payload": {
                                    "query": SUBSCRIPTION_QUERY,
                                    "variables": {"homeId": self.home_id},
                                },
                            }
                        )
                    )
                    async for message in websocket_client:
                        if self._stopped:
                            break
                        await self._handle_message(message)
            except WebSocketException as err:
                _LOGGER.warning("Realtime connection issue: %s", err)
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Unexpected realtime error: %s", err)
            await asyncio.sleep(10)

    async def _handle_message(self, raw: str) -> None:
        """Handle websocket message."""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            _LOGGER.debug("Non-JSON message: %s", raw)
            return
        if message.get("type") != "data":
            return
        payload = (
            message.get("payload", {})
            .get("data", {})
            .get("liveMeasurement", {})
        )
        if not payload:
            return
        self.last_payload = payload
        self.available_keys.update(payload.keys())
        await self._notify_listeners()

    async def _poll_loop(self) -> None:
        """Fallback polling using periodic HTTP query."""
        query = """
        query LiveMeasurementPoll($homeId: ID!) {
          liveMeasurement(homeId: $homeId) {
            timestamp
            power
            powerPhase1
            powerPhase2
            powerPhase3
            accumulatedConsumption
            currentL1
            currentL2
            currentL3
            voltagePhase1
            voltagePhase2
            voltagePhase3
          }
        }
        """
        while not self._stopped:
            try:
                resp = await self._post_graphql(query, {"homeId": self.home_id})
                payload = resp.get("data", {}).get("liveMeasurement") or {}
                if payload:
                    self.last_payload = payload
                    self.available_keys.update(payload.keys())
                    await self._notify_listeners()
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Polling failed: %s", err)
            await asyncio.sleep(60)

    @callback
    def add_listener(self, update_callback: Callable[[], None]) -> None:
        """Register listener for updates."""
        self._listeners.append(update_callback)

    @callback
    async def _notify_listeners(self) -> None:
        """Notify entities of new data."""
        for update in list(self._listeners):
            self._hass.add_job(update)

    def supports_key(self, key: str) -> bool:
        """Return True if key seen or expected."""
        return key in self.available_keys or bool(self.last_payload)
