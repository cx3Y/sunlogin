from datetime import timedelta
import logging

from homeassistant.components.sensor import DOMAIN as ENTITY_DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_DEVICES, 
    CONF_PLATFORM, 
    CONF_UNIT_OF_MEASUREMENT, 
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfEnergy,
)
import async_timeout
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONFIG, SL_DEVICES

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 3
SENSOR_TYPES = {
    "power": SensorEntityDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "voltage": SensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_visible_default=False,
    ),
    "current": SensorEntityDescription(
        key="current",
        translation_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "electricity_hour": SensorEntityDescription(
        key="electricity_hour",
        translation_key="electricity_hour",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "electricity_day": SensorEntityDescription(
        key="electricity_day",
        translation_key="electricity_day",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "electricity_week": SensorEntityDescription(
        key="electricity_week",
        translation_key="electricity_week",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "electricity_month": SensorEntityDescription(
        key="electricity_month",
        translation_key="electricity_month",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "electricity_lastmonth": SensorEntityDescription(
        key="electricity_lastmonth",
        translation_key="electricity_lastmonth",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    )
}


async def async_setup_entry(
    hass, config_entry, async_add_entities
):
    """Setup switch from a config entry created in the integrations UI."""
    entities = []

    for device in hass.data[DOMAIN][CONFIG][config_entry.entry_id][SL_DEVICES]:
        
        entities_to_setup = [
            entity
            for entity in device.entities.get(ENTITY_DOMAIN, [])
        ]

        if entities_to_setup:

            for entity in entities_to_setup:
                #_LOGGER.debug("sensor_types:%s" ,SENSOR_TYPES.get(entity))
                entities.append(
                    SunLoginHaSensor(
                        device,
                        entity,
                        SENSOR_TYPES.get(entity),
                    )
                )
    
    # async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug(entities)
    async_add_entities(entities)


class SunLoginHaSensor(SensorEntity, RestoreEntity):
    """Representation of a Tuya sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device,
        sensorid,
        description,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        
        # super().__init__(coordinator, context=sensorid)
        self.device = device
        self.dp_id = sensorid
        self.entity_description = description
        self._coordinator = device.update_manager.coordinator
        self.entity_id = f"{ENTITY_DOMAIN}.{self.device.model}_{self.device.sn}_{self.dp_id}"
        _LOGGER.debug("Initialized sensor [%s]", self.entity_id)

    @property
    def native_value(self):
        """Return sensor state."""
        return self.device.status(self.dp_id)


    # @property
    # def unit_of_measurement(self):
    #     """Return the unit of measurement of this entity, if any."""
    #     return self.device.status_unit[self.dp_id][CONF_UNIT_OF_MEASUREMENT]

    def _recv_data(self):
        """Receive data from the update coordinator.

        This event listener should be called by the coordinator whenever
        there is an update available.

        It works as a template for the _update_state() method, which should
        be overridden by child classes in order to update the state of the
        entities, when applicable.
        """
        if self._coordinator.last_update_success:
            self._update_state(self.device)
        self.async_write_ha_state()

    def _update_state(self, data):
        """Update the state of the entity.

        This method should be overridden by child classes in order to
        internalize state and attributes received from the coordinator.
        """

    async def async_added_to_hass(self):
        """Call when the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._recv_data))
        self.device._entities.append(self)

    @property
    def device_info(self):
        """Return device information for the device registry."""
        model = self.device.model
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.device.sn)
            },
            "name": self.device.name,
            "manufacturer": "SunLogin",
            "model": model,
            "sw_version": self.device.fw_version,
        }

    @property
    def should_poll(self):
        """Return if platform should poll for updates."""
        return False

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"sunlogin_{self.device.sn}_{self.dp_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return self.device.available(self.dp_id)
        # return self.device.update_manager.available

    # No need to restore state for a sensor

