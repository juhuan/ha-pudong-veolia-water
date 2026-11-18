"""Config flow for Shanghai Gas integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import selector

from .api import ShanghaiGasApiError, fetch_bills_sync
from .const import (
    CONF_CUSTOMER_ID,
    CONF_PG_HOST,
    CONF_PG_PORT,
    DEFAULT_PG_HOST,
    DEFAULT_PG_PORT,
    DOMAIN,
)


class ShanghaiGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shanghai Gas."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            customer_id = str(user_input[CONF_CUSTOMER_ID]).strip()
            pg_host = user_input.get(CONF_PG_HOST, DEFAULT_PG_HOST)
            pg_port = user_input.get(CONF_PG_PORT, DEFAULT_PG_PORT)

            await self.async_set_unique_id(customer_id)
            self._abort_if_unique_id_configured()

            def _validate() -> list[dict]:
                return fetch_bills_sync(customer_id, pg_host, pg_port)

            try:
                bills = await self.hass.async_add_executor_job(_validate)
            except ShanghaiGasApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                if not bills:
                    errors["base"] = "no_bills"
                else:
                    title = f"上海燃气 {customer_id}"
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_CUSTOMER_ID: customer_id,
                            CONF_PG_HOST: pg_host,
                            CONF_PG_PORT: pg_port,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_CUSTOMER_ID): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_PG_HOST, default=DEFAULT_PG_HOST): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_PG_PORT, default=DEFAULT_PG_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX, min=1, max=65535
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
