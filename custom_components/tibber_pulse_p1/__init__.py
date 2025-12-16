"""Setup for Tibber Pulse P1 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import CONF_DEVICE_ID, CONF_TOKEN, DOMAIN, PLATFORMS
from .coordinator import TibberPulseClient, TibberPulseCoordinator


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Handle YAML setup (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tibber Pulse P1 from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    client = TibberPulseClient(session=session, token=entry.data[CONF_TOKEN])
    coordinator = TibberPulseCoordinator(hass=hass, client=client, entry=entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_id": entry.data.get(CONF_DEVICE_ID),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
