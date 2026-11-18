"""The Pudong Veolia Water integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PudongVeoliaApiError, async_fetch_bills
from .const import DOMAIN, UPDATE_INTERVAL_HOURS

PLATFORMS: list[Platform] = [Platform.SENSOR]

type PudongVeoliaCoordinator = DataUpdateCoordinator[list[dict]]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pudong Veolia Water from a config entry."""
    account_id: str = entry.data["account_id"]
    session = async_get_clientsession(hass)

    async def _async_update_data() -> list[dict]:
        try:
            return await async_fetch_bills(session, account_id)
        except PudongVeoliaApiError as err:
            raise UpdateFailed(str(err)) from err

    coordinator: PudongVeoliaCoordinator = DataUpdateCoordinator(
        hass,
        logger=logging.getLogger(__name__),
        name=f"{DOMAIN}_{account_id}",
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
