"""Coordinator and client for Tibber Pulse P1."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)


class TibberPulseClientError(Exception):
    """Base error for Tibber Pulse client."""


class TibberPulseAuthError(TibberPulseClientError):
    """Authentication failed."""


class TibberPulseClient:
    """API helper for Tibber Data API."""

    def __init__(self, session: ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    async def async_get(self, path: str) -> dict[str, Any]:
        """Perform GET request."""
        url = f"{API_BASE}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.get(url, headers=headers, timeout=30) as resp:
                if resp.status in (401, 403):
                    raise TibberPulseAuthError("Invalid token")
                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as err:
            raise TibberPulseClientError(f"API error: {err.status}") from err
        except asyncio.TimeoutError as err:
            raise TibberPulseClientError("Request timed out") from err

    async def async_get_homes(self) -> list[dict[str, Any]]:
        """Return homes available to the token."""
        payload = await self.async_get("/homes")
        return payload.get("homes") or []

    async def async_get_devices(self, home_id: str) -> list[dict[str, Any]]:
        """Return devices for a home."""
        payload = await self.async_get(f"/homes/{home_id}/devices")
        return payload.get("devices") or []

    async def async_get_device(self, home_id: str, device_id: str) -> dict[str, Any]:
        """Return a device payload."""
        return await self.async_get(f"/homes/{home_id}/devices/{device_id}")


class TibberPulseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for polling Tibber Pulse P1 measurements."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TibberPulseClient,
        entry: ConfigEntry,
    ) -> None:
        self.client = client
        self.entry = entry
        self.home_id = entry.data[CONF_HOME_ID]
        self.home_name = entry.data.get(CONF_HOME_NAME, "Tibber Home")
        self.device_id = entry.data[CONF_DEVICE_ID]
        self.device_name = entry.data.get(CONF_DEVICE_NAME, "Tibber Pulse P1")
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.home_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for entities."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": MANUFACTURER,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest device data."""
        try:
            device_payload = await self.client.async_get_device(
                self.home_id, self.device_id
            )
            return device_payload
        except TibberPulseAuthError as err:
            raise ConfigEntryAuthFailed from err
        except TibberPulseClientError as err:
            raise UpdateFailed(str(err)) from err
