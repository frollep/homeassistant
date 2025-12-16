"""Config flow for Tibber Pulse P1."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_TOKEN,
    DOMAIN,
)
from .coordinator import TibberPulseAuthError, TibberPulseClient, TibberPulseClientError


def _client_from_token(hass: HomeAssistant, token: str) -> TibberPulseClient:
    """Build client for token."""
    session = aiohttp_client.async_get_clientsession(hass)
    return TibberPulseClient(session=session, token=token)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tibber Pulse P1."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str | None = None
        self._homes: list[dict] = []
        self._home_id: str | None = None
        self._home_name: str | None = None
        self._devices: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Ask for API token."""
        errors: dict[str, str] = {}
        if user_input:
            token = user_input[CONF_TOKEN].strip()
            client = _client_from_token(self.hass, token)
            try:
                self._homes = await client.async_get_homes()
            except TibberPulseAuthError:
                errors["base"] = "invalid_auth"
            except TibberPulseClientError:
                errors["base"] = "cannot_connect"
            else:
                if not self._homes:
                    errors["base"] = "no_homes"
                else:
                    self._token = token
                    if len(self._homes) == 1:
                        home = self._homes[0]
                        return await self._set_home_and_continue(home)
                    return await self.async_step_home()

        schema = vol.Schema({vol.Required(CONF_TOKEN): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_home(self, user_input: dict | None = None) -> FlowResult:
        """Let user pick home."""
        assert self._token is not None
        errors: dict[str, str] = {}
        options = {home["id"]: _friendly_home_name(home) for home in self._homes}
        if user_input:
            home_id = user_input[CONF_HOME_ID]
            home = next(h for h in self._homes if h["id"] == home_id)
            return await self._set_home_and_continue(home)

        schema = vol.Schema({vol.Required(CONF_HOME_ID): vol.In(options)})
        return self.async_show_form(step_id="home", data_schema=schema, errors=errors)

    async def async_step_device(self, user_input: dict | None = None) -> FlowResult:
        """Let user pick Pulse device."""
        assert self._token is not None
        assert self._home_id is not None
        errors: dict[str, str] = {}
        client = _client_from_token(self.hass, self._token)
        if not self._devices:
            try:
                self._devices = await client.async_get_devices(self._home_id)
            except TibberPulseAuthError:
                errors["base"] = "invalid_auth"
            except TibberPulseClientError:
                errors["base"] = "cannot_connect"
            if errors:
                return self.async_show_form(
                    step_id="device", data_schema=vol.Schema({}), errors=errors
                )
            if not self._devices:
                errors["base"] = "no_devices"
                return self.async_show_form(
                    step_id="device", data_schema=vol.Schema({}), errors=errors
                )

        preferred_devices = [
            d for d in self._devices if "pulse" in _device_label(d).casefold()
        ]
        device_list = preferred_devices or self._devices
        options = {device["id"]: _device_label(device) for device in device_list}

        if user_input:
            device_id = user_input[CONF_DEVICE_ID]
            device_name = options.get(device_id, "Tibber Pulse P1")
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=device_name,
                data={
                    CONF_TOKEN: self._token,
                    CONF_HOME_ID: self._home_id,
                    CONF_HOME_NAME: self._home_name,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                },
            )

        schema = vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)})
        return self.async_show_form(step_id="device", data_schema=schema, errors=errors)

    async def _set_home_and_continue(self, home: dict) -> FlowResult:
        """Persist selected home and move forward."""
        self._home_id = home["id"]
        self._home_name = _friendly_home_name(home)
        return await self.async_step_device()


def _friendly_home_name(home: dict) -> str:
    """Return friendly name for a home."""
    info = home.get("info") or {}
    nickname = info.get("name") or home.get("externalId")
    return nickname or home.get("id")


def _device_label(device: dict) -> str:
    """Return label for a device entry."""
    info = device.get("info") or {}
    name = info.get("name") or device.get("externalId") or "Device"
    brand = info.get("brand")
    model = info.get("model")
    suffix = " ".join(part for part in (brand, model) if part)
    if suffix:
        return f"{name} ({suffix})"
    return name
