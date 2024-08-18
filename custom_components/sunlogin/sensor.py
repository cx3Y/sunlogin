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
    "sub_power0": SensorEntityDescription(
        key="sub_power0",
        translation_key="sub_power0",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power1": SensorEntityDescription(
        key="sub_power1",
        translation_key="sub_power1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power2": SensorEntityDescription(
        key="sub_power2",
        translation_key="sub_power2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power3": SensorEntityDescription(
        key="sub_power3",
        translation_key="sub_power3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power4": SensorEntityDescription(
        key="sub_power4",
        translation_key="sub_power4",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power5": SensorEntityDescription(
        key="sub_power5",
        translation_key="sub_power5",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power6": SensorEntityDescription(
        key="sub_power6",
        translation_key="sub_power6",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=DEFAULT_PRECISION,
    ),
    "sub_power7": SensorEntityDescription(
        key="sub_power7",
        translation_key="sub_power7",
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
    "sub_current0": SensorEntityDescription(
        key="sub_current0",
        translation_key="sub_current0",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current1": SensorEntityDescription(
        key="sub_current1",
        translation_key="sub_current1",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current2": SensorEntityDescription(
        key="sub_current2",
        translation_key="sub_current2",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current3": SensorEntityDescription(
        key="sub_current3",
        translation_key="sub_current3",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current4": SensorEntityDescription(
        key="sub_current4",
        translation_key="sub_current4",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current5": SensorEntityDescription(
        key="sub_current5",
        translation_key="sub_current5",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current6": SensorEntityDescription(
        key="sub_current6",
        translation_key="sub_current6",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_current7": SensorEntityDescription(
        key="sub_current7",
        translation_key="sub_current7",
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
    "sub_electricity_hour0": SensorEntityDescription(
        key="sub_electricity_hour0",
        translation_key="sub_electricity_hour0",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour1": SensorEntityDescription(
        key="sub_electricity_hour1",
        translation_key="sub_electricity_hour1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour2": SensorEntityDescription(
        key="sub_electricity_hour2",
        translation_key="sub_electricity_hour2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour3": SensorEntityDescription(
        key="sub_electricity_hour3",
        translation_key="sub_electricity_hour3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour4": SensorEntityDescription(
        key="sub_electricity_hour4",
        translation_key="sub_electricity_hour4",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour5": SensorEntityDescription(
        key="sub_electricity_hour5",
        translation_key="sub_electricity_hour5",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour6": SensorEntityDescription(
        key="sub_electricity_hour6",
        translation_key="sub_electricity_hour6",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_hour7": SensorEntityDescription(
        key="sub_electricity_hour7",
        translation_key="sub_electricity_hour7",
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
    "sub_electricity_day0": SensorEntityDescription(
        key="sub_electricity_day0",
        translation_key="sub_electricity_day0",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day1": SensorEntityDescription(
        key="sub_electricity_day1",
        translation_key="sub_electricity_day1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day2": SensorEntityDescription(
        key="sub_electricity_day2",
        translation_key="sub_electricity_day2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day3": SensorEntityDescription(
        key="sub_electricity_day3",
        translation_key="sub_electricity_day3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day4": SensorEntityDescription(
        key="sub_electricity_day4",
        translation_key="sub_electricity_day4",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day5": SensorEntityDescription(
        key="sub_electricity_day5",
        translation_key="sub_electricity_day5",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day6": SensorEntityDescription(
        key="sub_electricity_day6",
        translation_key="sub_electricity_day6",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_day7": SensorEntityDescription(
        key="sub_electricity_day7",
        translation_key="sub_electricity_day7",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
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
    "sub_electricity_week0": SensorEntityDescription(
        key="sub_electricity_week0",
        translation_key="sub_electricity_week0",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week1": SensorEntityDescription(
        key="sub_electricity_week1",
        translation_key="sub_electricity_week1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week2": SensorEntityDescription(
        key="sub_electricity_week2",
        translation_key="sub_electricity_week2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week3": SensorEntityDescription(
        key="sub_electricity_week3",
        translation_key="sub_electricity_week3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week4": SensorEntityDescription(
        key="sub_electricity_week4",
        translation_key="sub_electricity_week4",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week5": SensorEntityDescription(
        key="sub_electricity_week5",
        translation_key="sub_electricity_week5",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week6": SensorEntityDescription(
        key="sub_electricity_week6",
        translation_key="sub_electricity_week6",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_week7": SensorEntityDescription(
        key="sub_electricity_week7",
        translation_key="sub_electricity_week7",
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
    "sub_electricity_month0": SensorEntityDescription(
        key="sub_electricity_month0",
        translation_key="sub_electricity_month0",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month1": SensorEntityDescription(
        key="sub_electricity_month1",
        translation_key="sub_electricity_month1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month2": SensorEntityDescription(
        key="sub_electricity_month2",
        translation_key="sub_electricity_month2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month3": SensorEntityDescription(
        key="sub_electricity_month3",
        translation_key="sub_electricity_month3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month4": SensorEntityDescription(
        key="sub_electricity_month4",
        translation_key="sub_electricity_month4",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month5": SensorEntityDescription(
        key="sub_electricity_month5",
        translation_key="sub_electricity_month5",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month6": SensorEntityDescription(
        key="sub_electricity_month6",
        translation_key="sub_electricity_month6",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_month7": SensorEntityDescription(
        key="sub_electricity_month7",
        translation_key="sub_electricity_month7",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
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
    ),
    "sub_electricity_lastmonth0": SensorEntityDescription(
        key="sub_electricity_lastmonth0",
        translation_key="sub_electricity_lastmonth0",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth1": SensorEntityDescription(
        key="sub_electricity_lastmonth1",
        translation_key="sub_electricity_lastmonth1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth2": SensorEntityDescription(
        key="sub_electricity_lastmonth2",
        translation_key="sub_electricity_lastmonth2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth3": SensorEntityDescription(
        key="sub_electricity_lastmonth3",
        translation_key="sub_electricity_lastmonth3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth4": SensorEntityDescription(
        key="sub_electricity_lastmonth4",
        translation_key="sub_electricity_lastmonth4",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth5": SensorEntityDescription(
        key="sub_electricity_lastmonth5",
        translation_key="sub_electricity_lastmonth5",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth6": SensorEntityDescription(
        key="sub_electricity_lastmonth6",
        translation_key="sub_electricity_lastmonth6",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
    "sub_electricity_lastmonth7": SensorEntityDescription(
        key="sub_electricity_lastmonth7",
        translation_key="sub_electricity_lastmonth7",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=DEFAULT_PRECISION,
        entity_registry_visible_default=False,
    ),
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
                    DeviceSensor(
                        device,
                        entity,
                        SENSOR_TYPES.get(entity),
                    )
                )
    
    # async_add_entities(sensors, update_before_add=True)
    # _LOGGER.debug(entities)
    async_add_entities(entities)


class DeviceSensor(SensorEntity, RestoreEntity):
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

        # self._update_state(self.device)
        self.async_write_ha_state()

    def _update_state(self, data):
        """Update the state of the entity.

        This method should be overridden by child classes in order to
        internalize state and attributes received from the coordinator.
        """

    async def async_added_to_hass(self):
        """Call when the entity is added to hass."""
        # self.async_on_remove(self._coordinator.async_add_listener(self._recv_data))
        self.device._entities[self.dp_id] = self

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

