"""Sensor platform for Tibber Pulse P1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DOMAIN
from .coordinator import TibberPulseCoordinator


def _normalize_capability_id(capability_id: str) -> str:
    """Normalize capability identifier to snake_case."""
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", capability_id)
    snake = snake.replace(".", "_").replace("-", "_")
    return re.sub(r"__+", "_", snake).lower()


def _convert_wh_to_kwh(value: float | int | None) -> float | None:
    """Convert Wh to kWh."""
    if value is None:
        return None
    return float(value) / 1000


def _identity(value: float | int | None) -> float | int | None:
    """Identity function."""
    return value


def _is_numeric_value(value: Any) -> bool:
    """Return True if value looks numeric."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            return False
        return True
    return False


def _coerce_number(value: Any) -> float | int | str | None:
    """Return a numeric type if possible."""
    if isinstance(value, (int, float)) or value is None:
        return value
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return value
        return number
    return value


@dataclass
class CapabilityDescription:
    """Description for a Tibber capability."""

    key: str
    ids: set[str]
    name: str
    native_unit_of_measurement: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT
    value_fn: Callable[[float | int | None], float | int | None] = _identity


CAPABILITY_SPECS: tuple[CapabilityDescription, ...] = (
    CapabilityDescription(
        key="power_total",
        ids={"power", "power_import", "active_power", "power_total", "power_net"},
        name="Power Total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    CapabilityDescription(
        key="power_export",
        ids={"power_export", "power_production", "active_power_export"},
        name="Power Export",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    CapabilityDescription(
        key="energy_total",
        ids={
            "accumulated_consumption",
            "energy_import_total",
            "last_meter_consumption",
        },
        name="Energy Imported",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    CapabilityDescription(
        key="energy_export_total",
        ids={"accumulated_production", "energy_export_total", "last_meter_production"},
        name="Energy Exported",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    CapabilityDescription(
        key="power_l1",
        ids={"power_phase1", "power_l1", "phase1_power"},
        name="Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    CapabilityDescription(
        key="power_l2",
        ids={"power_phase2", "power_l2", "phase2_power"},
        name="Power L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    CapabilityDescription(
        key="power_l3",
        ids={"power_phase3", "power_l3", "phase3_power"},
        name="Power L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    CapabilityDescription(
        key="voltage_l1",
        ids={"voltage_phase1", "voltage_l1", "phase1_voltage"},
        name="Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    CapabilityDescription(
        key="voltage_l2",
        ids={"voltage_phase2", "voltage_l2", "phase2_voltage"},
        name="Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    CapabilityDescription(
        key="voltage_l3",
        ids={"voltage_phase3", "voltage_l3", "phase3_voltage"},
        name="Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    CapabilityDescription(
        key="current_l1",
        ids={"current_l1", "phase1_current", "current_phase1"},
        name="Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
    ),
    CapabilityDescription(
        key="current_l2",
        ids={"current_l2", "phase2_current", "current_phase2"},
        name="Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
    ),
    CapabilityDescription(
        key="current_l3",
        ids={"current_l3", "phase3_current", "current_phase3"},
        name="Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
    ),
    CapabilityDescription(
        key="power_factor",
        ids={"power_factor"},
        name="Power Factor",
        state_class=None,
    ),
    CapabilityDescription(
        key="frequency",
        ids={"grid_frequency", "frequency"},
        name="Grid Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CapabilityDescription(
        key="temperature",
        ids={"temperature"},
        name="Device Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
)


def _match_capability(capability_id: str) -> CapabilityDescription | None:
    """Find matching description for capability id."""
    normalized = _normalize_capability_id(capability_id)
    for spec in CAPABILITY_SPECS:
        if normalized in spec.ids:
            return spec
    return None


def _iter_capabilities(device_payload: dict) -> Iterable[dict[str, Any]]:
    """Yield capability dicts from device payload."""
    for capability in device_payload.get("capabilities") or []:
        if not isinstance(capability, dict):
            continue
        cap_id = capability.get("id")
        if not cap_id:
            continue
        yield capability


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors."""
    coordinator: TibberPulseCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device_info = DeviceInfo(**coordinator.device_info)
    device_name = entry.data.get(CONF_DEVICE_NAME, "Tibber Pulse P1")

    entities: list[TibberPulseSensor] = []
    seen_keys: set[str] = set()

    for capability in _iter_capabilities(coordinator.data):
        cap_id = str(capability["id"])
        spec = _match_capability(cap_id)
        if spec:
            key = spec.key
            if key in seen_keys:
                continue
            seen_keys.add(key)
            entities.append(
                TibberPulseSensor(
                    coordinator=coordinator,
                    capability_id=cap_id,
                    description=spec,
                    device_info=device_info,
                    device_name=device_name,
                )
            )
        elif _is_numeric_value(capability.get("value")):
            key = _normalize_capability_id(cap_id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            name = capability.get("description") or capability.get("id")
            entities.append(
                TibberPulseSensor(
                    coordinator=coordinator,
                    capability_id=cap_id,
                    description=CapabilityDescription(
                        key=key,
                        ids={key},
                        name=name,
                        native_unit_of_measurement=capability.get("unit"),
                    ),
                    device_info=device_info,
                    device_name=device_name,
                )
            )

    if entities:
        async_add_entities(entities)


class TibberPulseSensor(CoordinatorEntity[TibberPulseCoordinator], SensorEntity):
    """Representation of a Tibber Pulse capability."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: TibberPulseCoordinator,
        capability_id: str,
        description: CapabilityDescription,
        device_info: DeviceInfo,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._capability_id = capability_id
        self.entity_description = SensorEntityDescription(
            key=description.key,
            name=f"{device_name} {description.name}",
            device_class=description.device_class,
            native_unit_of_measurement=description.native_unit_of_measurement,
            state_class=description.state_class,
        )
        self._description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        """Return availability."""
        return self._capability_id in {
            str(cap.get("id"))
            for cap in _iter_capabilities(self.coordinator.data)
        }

    @property
    def native_value(self) -> Any:
        """Return current value."""
        capability = self._get_capability()
        if not capability:
            return None
        raw_value = _coerce_number(capability.get("value"))
        if not isinstance(raw_value, (int, float)):
            return raw_value
        if (
            self._description.native_unit_of_measurement
            == UnitOfEnergy.KILO_WATT_HOUR
            and str(capability.get("unit", "")).lower() == "wh"
        ):
            return _convert_wh_to_kwh(raw_value)
        return self._description.value_fn(raw_value)

    def _get_capability(self) -> dict[str, Any] | None:
        """Return capability payload."""
        for capability in _iter_capabilities(self.coordinator.data):
            if str(capability.get("id")) == self._capability_id:
                return capability
        return None
