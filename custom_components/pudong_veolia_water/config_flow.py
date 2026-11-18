"""Config flow for Pudong Veolia Water."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PudongVeoliaApiError, async_fetch_bills
from .const import DOMAIN

DATA_SCHEMA = vol.Schema({vol.Required("account_id"): str})


class PudongVeoliaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pudong Veolia Water."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            account_id = str(user_input["account_id"]).strip()
            await self.async_set_unique_id(account_id)
            self._abort_if_unique_id_configured()

            try:
                bills = await async_fetch_bills(
                    async_get_clientsession(self.hass), account_id
                )
            except PudongVeoliaApiError:
                errors["base"] = "cannot_connect"
            else:
                address = bills[0].get("CUSTADDRESS", "")
                title = f"威立雅水费 {account_id}"
                if address:
                    title = f"{title} ({address})"
                return self.async_create_entry(title=title, data={"account_id": account_id})

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
