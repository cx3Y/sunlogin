from datetime import timedelta
import logging

from homeassistant.components.switch import DOMAIN as ENTITY_DOMAIN
from homeassistant.components.switch import (
    SwitchEntity, 
    SwitchEntityDescription,
    SwitchDeviceClass,
)
from homeassistant.const import CONF_DEVICES, CONF_PLATFORM
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONFIG, SL_DEVICES

_LOGGER = logging.getLogger(__name__)
SWITCH_TYPES = {
    "led": SwitchEntityDescription(
        key="led",
        translation_key="led",
        device_class=SwitchDeviceClass.SWITCH,
        entity_registry_visible_default=False,
    ),
    "def_st": SwitchEntityDescription(
        key="def_st",
        translation_key="def_st",
        device_class=SwitchDeviceClass.SWITCH,
        entity_registry_visible_default=False,
    ),
    "relay0": SwitchEntityDescription(
        key="relay0",
        translation_key="relay0",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay1": SwitchEntityDescription(
        key="relay1",
        translation_key="relay1",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay2": SwitchEntityDescription(
        key="relay2",
        translation_key="relay2",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay3": SwitchEntityDescription(
        key="relay3",
        translation_key="relay3",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay4": SwitchEntityDescription(
        key="relay4",
        translation_key="relay4",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay5": SwitchEntityDescription(
        key="relay5",
        translation_key="relay5",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay6": SwitchEntityDescription(
        key="relay6",
        translation_key="relay6",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "relay7": SwitchEntityDescription(
        key="relay7",
        translation_key="relay7",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "remote": SwitchEntityDescription(
        key="remote",
        translation_key="remote",
        device_class=SwitchDeviceClass.SWITCH,
        entity_registry_visible_default=False,
    )
}


async def async_setup_entry(
    hass, config_entry, async_add_entities
):
    """Setup switch from a config entry created in the integrations UI."""
    entities = []

    for device in hass.data[DOMAIN][CONFIG][config_entry.entry_id][SL_DEVICES]:

        _LOGGER.debug(device.entities)

        entities_to_setup = [
            entity
            for entity in device.entities.get(ENTITY_DOMAIN, [])
        ]

        if entities_to_setup:

            for entity in entities_to_setup:
                #_LOGGER.debug("switch_types: %s", SWITCH_TYPES.get(entity))
                entities.append(
                    SunLoginHaSwitch(
                        device,
                        entity,
                        SWITCH_TYPES.get(entity),
                    )
                )
    
    # async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug(entities)
    async_add_entities(entities)

class SunLoginHaSwitch(SwitchEntity, RestoreEntity):
    """Tuya Switch Device."""

    # ToggleEntity
    _attr_has_entity_name = True

    def __init__(
        self,
        device,
        switchid,
        description,
        **kwargs,
    ):
        # super().__init__(coordinator, context=switchid)
        self.device = device
        self.dp_id = switchid
        self.entity_description = description
        self._coordinator = device.update_manager.coordinator
        self.entity_id = f"{ENTITY_DOMAIN}.{self.device.model}_{self.device.sn}_{self.dp_id}"

        if (remark := device.memos.get(switchid)) is not None:
            self._attr_name = remark

        _LOGGER.debug("Initialized switch [%s]", self.entity_id)

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.device.status(self.dp_id)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.device.async_set_dp(self.dp_id, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self.device.async_set_dp(self.dp_id, 0)
        self.async_write_ha_state()

    def _recv_data(self):
        """Receive data from the update coordinator.

        This event listener should be called by the coordinator whenever
        there is an update available.

        It works as a template for the _update_state() method, which should
        be overridden by child classes in order to update the state of the
        entities, when applicable.
        """
        if self._coordinator.last_update_success:
            self._update_state(self._coordinator.data)
        self.async_write_ha_state()

    def _update_state(self, data):
        """Update the state of the entity.

        This method should be overridden by child classes in order to
        internalize state and attributes received from the coordinator.
        """

    async def async_added_to_hass(self):
        """Call when the entity is added to hass."""
        # state = await self.async_get_last_state()
        # _LOGGER.debug('last state %s %s', self.entity_id, state.state)
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



class FakeSunLoginHaSwitch(SwitchEntity):
    """Tuya Switch Device."""


    # ToggleEntity

    def __init__(
        self,
        device,
        switchid,
        **kwargs,
    ):
        self.device = device
        self.dp_id = switchid
        self._state = False
        self.entity_id = "switch.Test007_001122334455" + self.dp_id
        _LOGGER.debug("Initialized switch [%s]", self.dp_id)


    async def async_update(self):
        pass

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # return self._state
        return self._state

    def turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self._state = True

    def turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        self._state = False

    @property
    def device_info(self):
        """Return device information for the device registry."""
        model = "Test007"
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, '001122334455')
            },
            "name": "测试设备",
            "manufacturer": "SunLogin",
            "model": f"{model} (001122334455)",
            "sw_version": "0.0.1",
        }

    @property
    def name(self):
        """Get name of Sunlogin entity."""
        return self.dp_id

    @property
    def should_poll(self):
        """Return if platform should poll for updates."""
        return True

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"sunlogin_001122334455_{self.dp_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return  self.dp_id not in self.device.unavailable
        # return True
