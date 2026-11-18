"""Sensor platform for Pudong Veolia Water."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PudongVeoliaCoordinator
from .const import DOMAIN


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _period(bill: dict) -> str:
    return f"{bill.get('YEAR', '')}-{int(bill.get('MONTH', 0)):02d}"


@dataclass(frozen=True, kw_only=True)
class PudongVeoliaSensorDescription(SensorEntityDescription):
    """Describes a Pudong Veolia sensor."""

    value_fn: Callable[[dict], Any]


SENSORS: tuple[PudongVeoliaSensorDescription, ...] = (
    PudongVeoliaSensorDescription(
        key="total_payable",
        translation_key="total_payable",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-cny",
        value_fn=lambda b: _as_float(b.get("SUMPAY")),
    ),
    PudongVeoliaSensorDescription(
        key="water_usage",
        translation_key="water_usage",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water",
        value_fn=lambda b: _as_float(b.get("WATERNUM")),
    ),
    PudongVeoliaSensorDescription(
        key="sewage_volume",
        translation_key="sewage_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water-outline",
        value_fn=lambda b: _as_float(b.get("DIRTYNUM")),
    ),
    PudongVeoliaSensorDescription(
        key="water_fee",
        translation_key="water_fee",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:cash",
        value_fn=lambda b: _as_float(b.get("WATERFEE")),
    ),
    PudongVeoliaSensorDescription(
        key="sewage_fee",
        translation_key="sewage_fee",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:cash-outline",
        value_fn=lambda b: _as_float(b.get("DIRTYFEE")),
    ),
    PudongVeoliaSensorDescription(
        key="account_balance",
        translation_key="account_balance",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:wallet",
        value_fn=lambda b: _as_float(b.get("NOWLEFT")),
    ),
    PudongVeoliaSensorDescription(
        key="meter_reading",
        translation_key="meter_reading",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:gauge",
        value_fn=lambda b: _as_float(b.get("METERDATA")),
    ),
    PudongVeoliaSensorDescription(
        key="bill_status",
        translation_key="bill_status",
        icon="mdi:receipt-text-check-outline",
        value_fn=lambda b: "已缴" if str(b.get("BILLSTATUS")) == "1" else "未缴",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: PudongVeoliaCoordinator = entry.runtime_data
    async_add_entities(
        PudongVeoliaSensor(coordinator, entry, description)
        for description in SENSORS
    )


class PudongVeoliaSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Pudong Veolia bill sensor."""

    entity_description: PudongVeoliaSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PudongVeoliaCoordinator,
        entry: ConfigEntry,
        description: PudongVeoliaSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        account_id: str = entry.data["account_id"]
        self._attr_unique_id = f"{DOMAIN}_{account_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"威立雅水费 {account_id}",
            manufacturer="上海浦东威立雅自来水有限公司",
            model="威客服账单 (非官方接口)",
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        bill = self.coordinator.data[0]
        return {
            "account_id": bill.get("WATERMETERID"),
            "customer": bill.get("CUSTRNAME"),
            "address": bill.get("CUSTADDRESS"),
            "bill_period": _period(bill),
            "prev_meter_reading": _as_float(bill.get("PREVMETERDATA")),
            "meter_reading": _as_float(bill.get("METERDATA")),
            "copy_date": bill.get("COPYMETERDATE"),
            "pay_time": bill.get("PAYTIME"),
            "next_copy_date": bill.get("NEXTDATE"),
            "bill_status": "已缴" if str(bill.get("BILLSTATUS")) == "1" else "未缴",
            "water_price": _as_float(bill.get("WATERPRICE")),
            "sewage_price": _as_float(bill.get("DIRTYPRICE")),
            "history_periods": [
                {
                    "period": _period(b),
                    "water_usage": _as_float(b.get("WATERNUM")),
                    "sewage_volume": _as_float(b.get("DIRTYNUM")),
                    "total_payable": _as_float(b.get("SUMPAY")),
                    "bill_status": "已缴" if str(b.get("BILLSTATUS")) == "1" else "未缴",
                }
                for b in self.coordinator.data
            ],
        }
