"""The Shanghai Gas integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ShanghaiGasApiError, fetch_bills_sync
from .const import (
    CONF_CUSTOMER_ID,
    CONF_PG_HOST,
    CONF_PG_PORT,
    DEFAULT_PG_HOST,
    DEFAULT_PG_PORT,
    DOMAIN,
    UPDATE_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type ShanghaiGasCoordinator = DataUpdateCoordinator[list[dict]]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shanghai Gas from a config entry."""
    customer_id: str = entry.data[CONF_CUSTOMER_ID]
    pg_host: str = entry.data.get(CONF_PG_HOST, DEFAULT_PG_HOST)
    pg_port: int = entry.data.get(CONF_PG_PORT, DEFAULT_PG_PORT)

    async def _async_update_data() -> list[dict]:
        try:
            return await hass.async_add_executor_job(
                fetch_bills_sync, customer_id, pg_host, pg_port
            )
        except ShanghaiGasApiError as err:
            raise UpdateFailed(str(err)) from err

    coordinator: ShanghaiGasCoordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name=f"{DOMAIN}_{customer_id}",
        update_method=_async_update_data,
        update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
