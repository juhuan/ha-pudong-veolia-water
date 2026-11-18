"""Sensor platform for Shanghai Gas."""

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

from . import ShanghaiGasCoordinator
from .const import CONF_CUSTOMER_ID, DOMAIN


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class ShanghaiGasSensorDescription(SensorEntityDescription):
    """Describes a Shanghai Gas sensor."""

    value_fn: Callable[[dict], Any]


SENSORS: tuple[ShanghaiGasSensorDescription, ...] = (
    ShanghaiGasSensorDescription(
        key="bill_amount",
        translation_key="bill_amount",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:currency-cny",
        value_fn=lambda b: _as_float(b.get("money")),
    ),
    ShanghaiGasSensorDescription(
        key="consumption",
        translation_key="consumption",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:fire",
        value_fn=lambda b: _as_float(b.get("consumption")),
    ),
    ShanghaiGasSensorDescription(
        key="year_consumption",
        translation_key="year_consumption",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:fire-outline",
        value_fn=lambda b: _as_float(b.get("year_consumption")),
    ),
    ShanghaiGasSensorDescription(
        key="meter_reading",
        translation_key="meter_reading",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:gauge",
        value_fn=lambda b: _as_float(b.get("current_reading")),
    ),
    ShanghaiGasSensorDescription(
        key="account_balance",
        translation_key="account_balance",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:wallet",
        value_fn=lambda b: _as_float(b.get("current_balance")),
    ),
    ShanghaiGasSensorDescription(
        key="gas_price",
        translation_key="gas_price",
        native_unit_of_measurement="CNY/m³",
        icon="mdi:tag",
        value_fn=lambda b: _as_float(b.get("price")),
    ),
    ShanghaiGasSensorDescription(
        key="ladder_total",
        translation_key="ladder_total",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:stairs",
        value_fn=lambda b: _as_float(b.get("ladder_total")),
    ),
    ShanghaiGasSensorDescription(
        key="payment_status",
        translation_key="payment_status",
        icon="mdi:receipt-text-check-outline",
        value_fn=lambda b: b.get("payment_status"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: ShanghaiGasCoordinator = entry.runtime_data
    async_add_entities(
        ShanghaiGasSensor(coordinator, entry, description) for description in SENSORS
    )


class ShanghaiGasSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Shanghai Gas sensor."""

    entity_description: ShanghaiGasSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ShanghaiGasCoordinator,
        entry: ConfigEntry,
        description: ShanghaiGasSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        customer_id: str = entry.data[CONF_CUSTOMER_ID]
        self._attr_unique_id = f"{DOMAIN}_{customer_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, customer_id)},
            name=f"上海燃气 {customer_id}",
            manufacturer="上海燃气有限公司",
            model="微客服账单 (pfm 中转)",
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
            "customer": bill.get("customer_name"),
            "address": bill.get("customer_address"),
            "bill_period": bill.get("bill_ym"),
            "payment_status": bill.get("payment_status"),
            "billing_type": bill.get("billing_type"),
            "read_status": bill.get("read_status"),
            "last_reading": _as_float(bill.get("last_reading")),
            "current_reading": _as_float(bill.get("current_reading")),
            "meter_delta": _as_float(bill.get("meter_delta")),
            "overdue_fine": _as_float(bill.get("overdue_fine")),
            "pure_fee": _as_float(bill.get("pure_fee")),
            "last_balance": _as_float(bill.get("last_balance")),
            "current_balance": _as_float(bill.get("current_balance")),
            "first_count": _as_float(bill.get("first_count")),
            "second_count": _as_float(bill.get("second_count")),
            "third_count": _as_float(bill.get("third_count")),
            "first_money": _as_float(bill.get("first_money")),
            "second_money": _as_float(bill.get("second_money")),
            "third_money": _as_float(bill.get("third_money")),
            "read_date": bill.get("read_date"),
            "billing_date": bill.get("billing_date"),
            "next_read_date": bill.get("next_read_date"),
            "last_payday": bill.get("last_payday"),
            "fetched_at": bill.get("fetched_at"),
            "history_periods": [
                {
                    "period": b.get("bill_ym"),
                    "consumption": _as_float(b.get("consumption")),
                    "money": _as_float(b.get("money")),
                    "payment_status": b.get("payment_status"),
                }
                for b in self.coordinator.data
            ],
        }
