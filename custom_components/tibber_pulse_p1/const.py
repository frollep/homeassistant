"""Constants for Tibber Pulse P1 integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "tibber_pulse_p1"
PLATFORMS = [Platform.SENSOR]

CONF_TOKEN = "token"
CONF_HOME_ID = "home_id"
CONF_HOME_NAME = "home_name"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"

API_BASE = "https://data-api.tibber.com/v1"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)
MANUFACTURER = "Tibber"
