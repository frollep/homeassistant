"""Sensor platform for Tibber Pulse Phases."""

from __future__ import annotations

from dataclasses import dataclass

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
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_HOME_ID, CONF_HOME_NAME, DOMAIN
from . import TibberPulseHub


@dataclass
class TibberPulseSensorDescription(SensorEntityDescription):
    """Describes Tibber sensor."""

    source: str | None = None


SENSORS: tuple[TibberPulseSensorDescription, ...] = (
    TibberPulseSensorDescription(
        key="power_total",
        name="Power Total",
        source="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="energy_total",
        name="Energy Total",
        source="accumulatedConsumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    TibberPulseSensorDescription(
        key="power_l1",
        name="Power L1",
        source="powerPhase1",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="power_l2",
        name="Power L2",
        source="powerPhase2",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="power_l3",
        name="Power L3",
        source="powerPhase3",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="current_l1",
        name="Current L1",
        source="currentL1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="current_l2",
        name="Current L2",
        source="currentL2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="current_l3",
        name="Current L3",
        source="currentL3",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="voltage_l1",
        name="Voltage L1",
        source="voltagePhase1",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="voltage_l2",
        name="Voltage L2",
        source="voltagePhase2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TibberPulseSensorDescription(
        key="voltage_l3",
        name="Voltage L3",
        source="voltagePhase3",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tibber sensors."""
    hub: TibberPulseHub = hass.data[DOMAIN][entry.entry_id]
    entities = [
        TibberPulseSensor(hub, entry, description)
        for description in SENSORS
    ]
    async_add_entities(entities)


class TibberPulseSensor(SensorEntity):
    """Representation of a Tibber sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hub: TibberPulseHub,
        entry: ConfigEntry,
        description: TibberPulseSensorDescription,
    ) -> None:
        self.entity_description = description
        self._hub = hub
        self._attr_name = f"{hub.home_name} {description.name}"
        self._attr_unique_id = f"{hub.home_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.home_id)},
            name=hub.home_name,
            manufacturer="Tibber",
        )

    @property
    def available(self) -> bool:
        """Return if sensor has seen data."""
        source = self.entity_description.source
        return bool(source and self._hub.supports_key(source))

    @property
    def native_value(self):
        """Return current value."""
        source = self.entity_description.source
        if not source:
            return None
        return self._hub.last_payload.get(source)

    async def async_added_to_hass(self) -> None:
        """Register callback."""
        self._hub.add_listener(self._schedule_immediate_update)

    @callback
    def _schedule_immediate_update(self) -> None:
        """Schedule entity state update."""
        self.async_write_ha_state()
