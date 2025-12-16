"""Diagnostics support."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, DOMAIN

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub = hass.data[DOMAIN].get(entry.entry_id)
    data = {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "last_payload_keys": sorted(getattr(hub, "available_keys", []))
        if hub
        else [],
    }
    return data
