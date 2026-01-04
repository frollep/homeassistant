"""Setup for Tibber Pulse P1 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_TOKEN, DOMAIN, PLATFORMS
from .coordinator import TibberPulseCoordinator


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Handle YAML setup (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tibber Pulse P1 from a config entry."""
    coordinator = TibberPulseCoordinator(hass=hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_id": entry.data.get(CONF_DEVICE_ID),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: TibberPulseCoordinator | None = (
        hass.data.get(DOMAIN, {})
        .get(entry.entry_id, {})
        .get("coordinator")
    )
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if coordinator:
            await coordinator.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
