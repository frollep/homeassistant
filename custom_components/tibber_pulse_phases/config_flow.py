"""Config flow for Tibber Pulse Phases."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_HOME_ID, CONF_HOME_NAME, CONF_TOKEN, DOMAIN, HTTP_URL


async def _fetch_homes(hass: HomeAssistant, token: str) -> list[dict]:
    """Fetch homes with token."""
    query = """
    query ViewerHomes {
      viewer {
        homes {
          id
          appNickname
          address { address1 }
        }
      }
    }
    """
    session = aiohttp_client.async_get_clientsession(hass)
    async with session.post(
        HTTP_URL,
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if "errors" in data:
        raise ValueError(str(data["errors"]))
    return data.get("data", {}).get("viewer", {}).get("homes", []) or []


class TibberPulseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str | None = None
        self._homes: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """First step."""
        errors: dict[str, str] = {}
        if user_input:
            token = user_input[CONF_TOKEN].strip()
            try:
                self._homes = await _fetch_homes(self.hass, token)
                self._token = token
            except aiohttp.ClientResponseError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                if not self._homes:
                    errors["base"] = "no_homes"
                else:
                    return await self.async_step_home()
        schema = vol.Schema({vol.Required(CONF_TOKEN): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_home(self, user_input: dict | None = None) -> FlowResult:
        """Select home."""
        assert self._token  # token set in previous step
        errors: dict[str, str] = {}
        options = {
            home["id"]: home.get("appNickname") or home.get("address", {}).get("address1")
            for home in self._homes
        }
        if user_input:
            home_id = user_input[CONF_HOME_ID]
            home_name = options.get(home_id, "Tibber Home")
            await self.async_set_unique_id(home_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Tibber {home_name}",
                data={
                    CONF_TOKEN: self._token,
                    CONF_HOME_ID: home_id,
                    CONF_HOME_NAME: home_name,
                },
            )

        schema = vol.Schema({vol.Required(CONF_HOME_ID): vol.In(options)})
        return self.async_show_form(step_id="home", data_schema=schema, errors=errors)
