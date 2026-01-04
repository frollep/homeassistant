"""Config flow for Tibber Pulse P1."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from tibber import Tibber
from tibber.exceptions import InvalidLoginError, RetryableHttpExceptionError

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_TOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tibber Pulse P1."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str | None = None
        self._homes: list[dict] = []
        self._home_id: str | None = None
        self._home_name: str | None = None
        self._homes_raw: list = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Ask for API token (or reuse existing Tibber integration token)."""
        errors: dict[str, str] = {}
        existing = self._get_existing_token()

        if user_input is None:
            if existing:
                _LOGGER.warning("tibber_pulse_p1: trying existing Tibber token on init")
                result = await self._try_token(existing)
                if result is True:
                    return await self._continue_after_homes()
                errors["base"] = result

        if user_input:
            raw = user_input.get(CONF_TOKEN, "")
            token = raw.strip()
            if not token:
                token = self._get_existing_token()
                if not token:
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.warning("tibber_pulse_p1: token empty, reusing existing Tibber token")
                    result = await self._try_token(token)
                    if result is True:
                        return await self._continue_after_homes()
                    errors["base"] = result
            else:
                _LOGGER.warning("tibber_pulse_p1: token provided manually")
                result = await self._try_token(token)
                if result is True:
                    return await self._continue_after_homes()
                errors["base"] = result

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN, default=existing or ""): str}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _get_existing_token(self) -> str | None:
        """Return token from existing Tibber integration if available."""
        for entry in self.hass.config_entries.async_entries("tibber"):
            token = entry.data.get("access_token")
            if token:
                _LOGGER.debug("Found Tibber token in entry %s", entry.entry_id)
                return token
        return None

    async def _try_token(self, token: str) -> str | bool:
        """Validate token and populate homes."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        client = Tibber(
            access_token=token,
            websession=session,
            user_agent="HomeAssistant tibber_pulse_p1",
        )
        try:
            await client.update_info()
            homes = client.get_homes(only_active=False)
        except RetryableHttpExceptionError:
            _LOGGER.warning(
                "tibber_pulse_p1: temporary error while validating token (rate limited?)"
            )
            return "cannot_connect"
        except InvalidLoginError:
            _LOGGER.warning("tibber_pulse_p1: token rejected by Tibber (InvalidLoginError)")
            return "invalid_auth"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("tibber_pulse_p1: error while validating token")
            return "cannot_connect"

        if not homes:
            _LOGGER.warning("tibber_pulse_p1: no homes returned for token")
            return "no_homes"

        self._token = token
        self._homes_raw = homes
        _LOGGER.warning("tibber_pulse_p1: token OK, homes=%s", [h.home_id for h in homes])
        self._homes = [
            {
                "id": home.home_id,
                "info": {"name": getattr(home, "app_nickname", None)}
                if hasattr(home, "app_nickname")
                else {},
            }
            for home in homes
        ]
        return True

    async def _continue_after_homes(self) -> FlowResult:
        """Proceed to home/device selection after homes are loaded."""
        if len(self._homes) == 1:
            return await self._set_home_and_continue(self._homes[0])
        return await self.async_step_home()

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
        # With GraphQL we use the home itself as the device.
        assert self._token is not None
        assert self._home_id is not None
        device_id = self._home_id
        device_name = self._home_name or "Tibber Pulse P1"
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
