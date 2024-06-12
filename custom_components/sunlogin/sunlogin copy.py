import functools
import hashlib
import json
import logging
import time
import uuid
import base64
import asyncio
import requests
import async_timeout
import aiohttp
from .sunlogin_api import CloudAPI, CloudAPI_V2, PlugAPI_V1, PlugAPI_V2
# from .sunlogin_api import PlugAPI_V2 as PlugAPI
from datetime import timedelta, datetime, timezone

from abc import ABC, abstractmethod
from urllib.parse import urlencode
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers.restore_state import async_get
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from homeassistant import config_entries
from homeassistant.const import (
    CONF_UNIT_OF_MEASUREMENT,
    CONF_PLATFORM,
    CONF_DEVICES,
)

from .const import (
    DOMAIN,
    SL_DEVICES,
    BLANK_SN,
    CONFIG,
    CONF_TOKEN,
    CONF_DEVICE_SN,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_MEMOS,
    CONF_DEVICE_VERSION,
    CONF_DEVICE_ADDRESS,
    CONF_DEVICE_IP_ADDRESS,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_EXPIRE,
)

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed
)

_LOGGER = logging.getLogger(__name__)

HTTP_SUFFIX = 'http://'
LOCAL_PORT = ':6767'

ELECTRIC_MODEL = ["C1-2", "C2", "C2_BLE", "C2-BLE", "P1", "P1Pro", "P4"]   #, "SunLogin generic"
NO_ELECTRIC_MODEL = ["C1", "C1Pro", "C1Pro_BLE", "C1Pro-BLE", "P2"]
DP_RELAY_0 = "relay0"
DP_RELAY_1 = "relay1"
DP_RELAY_2 = "relay2"
DP_RELAY_3 = "relay3"
DP_RELAY_4 = "relay4"
DP_RELAY_5 = "relay5"
DP_RELAY_6 = "relay6"
DP_RELAY_7 = "relay7"
DP_LED = "led"
DP_DEFAULT = "def_st"
DP_REMOTE = "remote"
DP_RELAY = "response"
DP_ELECTRIC = "electric"
DP_POWER = "power"
DP_CURRENT = "current"
DP_VOLTAGE = "voltage"
DP_ELECTRICITY_HOUR = "electricity_hour"
DP_ELECTRICITY_DAY = "electricity_day"
DP_ELECTRICITY_WEEK = "electricity_week"
DP_ELECTRICITY_MONTH = "electricity_month"
DP_ELECTRICITY_LASTMONTH = "electricity_lastmonth"

PLATFORM_OF_ENTITY = {
    DP_LED: "switch",
    DP_DEFAULT: "switch",
    DP_RELAY_0: "switch",
    DP_RELAY_1: "switch",
    DP_RELAY_2: "switch",
    DP_RELAY_3: "switch",
    DP_RELAY_4: "switch",
    DP_RELAY_5: "switch",
    DP_RELAY_6: "switch",
    DP_RELAY_7: "switch",
    DP_REMOTE: "switch",
    DP_ELECTRIC: "sensor",
    DP_POWER: "sensor",
    DP_CURRENT: "sensor",
    DP_VOLTAGE: "sensor",
    DP_ELECTRICITY_HOUR: "sensor",
    DP_ELECTRICITY_DAY: "sensor",
    DP_ELECTRICITY_WEEK: "sensor",
    DP_ELECTRICITY_MONTH: "sensor",
    DP_ELECTRICITY_LASTMONTH: "sensor",
}
SLOT_1_WITH_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
    DP_POWER: 0,
    DP_CURRENT: 0,
    DP_VOLTAGE: 0,
}
SLOT_1_WITHOUT_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
}
SLOT_3_WITH_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
    DP_RELAY_1: 0,
    DP_RELAY_2: 0,
    DP_POWER: 0,
    DP_CURRENT: 0,
    DP_VOLTAGE: 0,
}
SLOT_3_WITHOUT_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
    DP_RELAY_1: 0,
    DP_RELAY_2: 0,
}
SLOT_4_WITH_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
    DP_RELAY_1: 0,
    DP_RELAY_2: 0,
    DP_RELAY_3: 0,
    DP_POWER: 0,
    DP_CURRENT: 0,
    DP_VOLTAGE: 0,
}
SLOT_4_WITHOUT_ELECTRIC = {
    DP_LED: 0,
    DP_DEFAULT: 0,
    DP_RELAY_0: 0,
    DP_RELAY_1: 0,
    DP_RELAY_2: 0,
    DP_RELAY_3: 0,
}
SLOT_X_WITH_ELECTRIC = []
SLOT_X_WITHOUT_ELECTRIC = []

async def async_request_error_process(func, *args):
    error = None
    resp = None
    try:
        resp = await func(*args)
    except requests.exceptions.ConnectionError:
        error = "Request failed, status ConnectionError"
        return error, resp
    
    if not resp.ok:
        try: 
            r_json = resp.json()
        except: 
            error = "Response can't cover to JSON"
            return error, resp
        error = r_json.get('error', 'unkown')
        return error, resp
    
    return error, resp

def get_sunlogin_device(hass, config):
    model = config.get(CONF_DEVICE_MODEL)
    if 'C2' in model or 'C1-2' == model:
        return C2(hass, config)
    elif 'C1' in model:
        return C1Pro(hass, config)
    elif 'P1' in model:
        return P1Pro(hass, config)
    elif 'P2' in model:
        pass
    elif 'P4' in model:
        pass
    else:
        pass

def get_plug_entries(config):
    model = config.get(CONF_DEVICE_MODEL) 
    entities = {}

    if model in ["P1", "P1Pro"]:
        status = SLOT_4_WITH_ELECTRIC.copy()
    elif model in ["C1-2", "C2", "C2_BLE", "C2-BLE"]:
        status = SLOT_1_WITH_ELECTRIC.copy()
    elif model in ["P4"]:
        status = SLOT_3_WITH_ELECTRIC.copy()
    elif model in ["C1", "C1Pro", "C1Pro_BLE", "C1Pro-BLE"]:
        status = SLOT_1_WITHOUT_ELECTRIC.copy()
    elif model in ["P2"]:
        status = SLOT_3_WITHOUT_ELECTRIC.copy()
            # status.pop(DP_LED)
    else:
        pass
    
    if config.get(CONF_DEVICE_ADDRESS) is not None:
        if model in ELECTRIC_MODEL:
            status[DP_ELECTRICITY_HOUR] = 0
            status[DP_ELECTRICITY_DAY] = 0
            status[DP_ELECTRICITY_WEEK] = 0
            status[DP_ELECTRICITY_MONTH] = 0
            status[DP_ELECTRICITY_LASTMONTH] = 0
        status[DP_REMOTE] = 1

    for dp_id,_ in status.items():
        platform = PLATFORM_OF_ENTITY[dp_id]
        if entities.get(platform) is None:
            entities[platform] = [dp_id]
        else:
            entities[platform].append(dp_id)
    
    return entities

def get_plug_memos(config):
    memos = {}

    for item in config.get(CONF_DEVICE_MEMOS, []):
        index = item.get('number', 0)
        name = item.get('name')
        if name is not None:
            memos.update({f'relay{index}': name})

    return memos
    

def plug_status_process(data):
    status = {}
    for relay_status in data.get(DP_RELAY, ''):
        index = relay_status['index']
        value = relay_status['status']
        status[f"relay{index}"]= value
    if (led := data.get(DP_LED)) is not None:
        status[DP_LED] = led
    
    if (default := data.get(DP_DEFAULT)) is not None:
        status[DP_DEFAULT] = default

    return status

def plug_electric_process(data):
    status = {}
    if (voltage := data.get('vol')) is not None:
        status[DP_VOLTAGE] = voltage

    if (current := data.get('curr')) is not None:
        current = current // 1000
        status[DP_CURRENT] = current

    if (power := data.get('power')) is not None:
        power = power / 1000
        status[DP_POWER] = power

    return status

def plug_power_consumes_process(data):
    status = {}
    if len(data) > 0:
        # self.req_time = max(r_json[0].get('endtime', 0), self.req_time)
        # func = lambda itme: itme.get('starttime', 0)
        # r_json.sort(key=func)
        _monday = 946828800 #2000-1-3 00:00:00 utc+8 
        data = data[:24*30*2]
        Hour = 0
        Day = 0
        Week = 0
        Month = 0
        LastMonth = 0

        _t = time.time()
        if time.time() - data[0].get('endtime') <= 3660:
            Hour = data[0].get('consume', 0)
        
        # _offset = ((time.gmtime().tm_hour+8)%24)*3600
        _offset = (_t - _monday) % (24*3600)
        for d in data:
            if _t - d.get('endtime') < _offset:
                Day += d.get('consume')
            else: break
        
        _offset = (_t - _monday) % (7*24*3600)
        for d in data:
            if _t - d.get('endtime') < _offset:
                Week += d.get('consume')
            else: break

        _offset = _t + 8*3600 - datetime.timestamp(datetime.fromtimestamp(_t+8*3600, timezone.utc).replace(day=1))
        for d in data:
            if _t - d.get('endtime') < _offset:
                Month += d.get('consume')
            else: break

        _offset = _t + 8*3600 - datetime.timestamp((datetime.fromtimestamp(_t+8*3600, timezone.utc).replace(day=1) - timedelta(days=1)).replace(day=1))
        for d in data:
            if _t - d.get('endtime') < _offset:
                LastMonth += d.get('consume')
            else: break
        
        if Hour > 0:
            status[DP_ELECTRICITY_HOUR] = Hour
        if Day > 0:
            status[DP_ELECTRICITY_DAY] = Day
        if Week > 0:
            status[DP_ELECTRICITY_WEEK] = Week
        if Month > 0:
            status[DP_ELECTRICITY_MONTH] = Month
        if LastMonth - Month > 0:
            status[DP_ELECTRICITY_LASTMONTH] = LastMonth - Month

    return status

def get_current_token(hass):
    entry_id = config_entries.current_entry.get().entry_id
    token = hass.data[DOMAIN][CONFIG][entry_id][CONF_TOKEN]
    return token

def toekn_decode(access_token):
    part1, part2, part3 = access_token.split('.')
    part2 += '='*(4-(len(part2)%4))
    info = json.loads(base64.b64decode(part2).decode('utf-8'))
    return info

def update_device_configuration(hass, sn, data):
    _LOGGER.debug("in update_device_configuration")
    _LOGGER.debug("%s %s", sn, data)
    entry = config_entries.current_entry.get()
    new_data = {**entry.data}
    device_config = new_data[CONF_DEVICES][sn]
    new_data[CONF_DEVICES][sn].update(data)
    _LOGGER.debug(device_config)
    # new_data[CONF_DEVICES][sn] = device_config
    _LOGGER.debug(new_data)
    hass.config_entries.async_update_entry(entry, data=new_data)
    _LOGGER.debug("out update_device_configuration")
    
    
    

class SunLogin:
    def __init__(self, hass):
        """Initialize the class."""
        self.hass = hass
        self.access_token = ''
        self.refresh_token = ''
        self.refresh_expire = 0
        self.userid = None
        self._api_v1 = CloudAPI(hass)
        self._api_v2 = CloudAPI_V2(hass)
        self.device_list = {}

    async def async_get_access_token_by_password(self, username, password):
        error, resp = await async_request_error_process(self._api_v1.async_login_by_password, username, password)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.access_token = r_json.get(CONF_ACCESS_TOKEN, '')
        self.refresh_token = r_json.get(CONF_REFRESH_TOKEN, '')
        self.refresh_expire = time.time()
        
        return "ok"

    async def async_get_access_token_by_sms(self, username, smscode):

        error, resp = await async_request_error_process(self._api_v1.async_login_by_sms, username, smscode)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.access_token = r_json.get(CONF_ACCESS_TOKEN, '')
        self.refresh_token = r_json.get(CONF_REFRESH_TOKEN, '')
        self.refresh_expire = time.time()
        
        return "ok"
    
    async def async_get_access_token_by_qrcode(self, secret):
        error, resp = await async_request_error_process(self._api_v2.async_login_by_qrcode, secret)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.access_token = r_json.get(CONF_ACCESS_TOKEN, '')
        self.refresh_token = r_json.get(CONF_REFRESH_TOKEN, '')
        self.refresh_expire = time.time()
        self.userid = r_json.get('userid')

        return "ok"    

    async def async_get_devices_list(self):
        error, resp = await async_request_error_process(self._api_v1.async_get_devices_list, self.access_token)

        if error is not None:
            return error
        
        r_json = resp.json()
        if len(r_json.get('devices', '')):
            self.device_list = {dev["sn"]: dev for dev in r_json["devices"]}
        
            return "ok"    
            
        return "No device"
    

class SunLoginDevice(ABC):
    hass = None
    config = None
    api = None
    update_manager = None
    _entities = list()
    _sn = BLANK_SN
    _fw_version = "0.0.0"
        # self.reset_jobs: list[CALLBACK_TYPE] = []

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.config.get(CONF_DEVICE_NAME, 'SunLogin Device')##

    @property
    def device_type(self) -> str:
        return self.config.get(CONF_DEVICE_TYPE, 'unknow')
    
    @property
    def model(self) -> str:
        return self.config.get(CONF_DEVICE_MODEL, 'SunLogin generic')
    
    @property
    def sn(self) -> str:
        return self._sn
    
    @sn.setter
    def sn(self, sn):
        if sn is not None:
            self._sn = sn

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the device."""
        return self.config.get(CONF_DEVICE_SN)

    @property
    def mac_address(self) -> str:
        """Return the mac address of the device."""
        return self.config.get(CONF_DEVICE_MAC)

    @property
    def available(self) -> bool | None:
        """Return True if the device is available."""
        if self.update_manager is None:
            return False
        return self.update_manager.available

    @property
    def fw_version(self):
        return self._fw_version
    
    @fw_version.setter
    def fw_version(self, fw_version):
        self._fw_version = fw_version

    @staticmethod
    async def async_update(hass, entry) -> None:
        """Update the device and related entities.

        Triggered when the device is renamed on the frontend.
        """
        device_registry = dr.async_get(hass)
        assert entry.unique_id
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.unique_id)}
        )
        assert device_entry
        device_registry.async_update_device(device_entry.id, name=entry.title)
        await hass.config_entries.async_reload(entry.entry_id)

    def _set_scan_interval(self, scan_interval):
        # scan_interval = timedelta(seconds=seconds)
        self.update_manager.coordinator.update_interval = scan_interval

    async def async_unload(self) -> bool:
        """Unload the device and related entities."""
        if self.update_manager is None:
            return True

        while self.reset_jobs:
            self.reset_jobs.pop()()

        return await self.hass.config_entries.async_unload_platforms(
            self.config, ''
        )


class PlugDevice(SunLoginDevice, ABC):
    
    _ip = None
    _status = dict()
    new_data = dict()
    update_manager = None
    
    @property
    def remote_address(self):
        return self.config.get(CONF_DEVICE_ADDRESS)
    
    @property
    def local_address(self):
        if self._ip is not None: 
            return HTTP_SUFFIX + self._ip + LOCAL_PORT
        elif (ip := self.config.get('ip')) is not None:
            return HTTP_SUFFIX + ip + LOCAL_PORT
    
    def status(self, dp_id):
        # status = self.update_manager.coordinator.data
        # return status[dpid]
        return self._status.get(dp_id)
        # return self.update_manager.coordinator.data[dpid]
    
    def set_dp_remote(self, status):
        _LOGGER.debug(self.remote_address)
        _LOGGER.debug(self.local_address)
        if status is None:
            return
        elif status and self.remote_address is not None:
            # self.api = PlugAPI(self.hass, self.remote_address)
            self.api.address = self.remote_address
            self._status.update({DP_REMOTE: status})
        elif not status and self.local_address is not None:
            # self.api = PlugAPI(self.hass, self.local_address)
            self.api.address = self.local_address
            self._status.update({DP_REMOTE: status})
        # store dp_remote status
        # entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        # async_get(self.hass).async_restore_entity_added(entity)

    def get_entity(self, unique_id):
        for entity in self._entities:
            if unique_id == entity.unique_id:
                return entity
            
    def get_sn_by_configuration(self):
        return self.config.get(CONF_DEVICE_SN)
    
    def update_configuration(self):
        if len(self.new_data) > 0:
            try:
                update_device_configuration(self.hass, self.get_sn_by_configuration(), self.new_data)
                self.new_data = dict()
            except:
                _LOGGER.debug('update_device_configuration failed')
        
    async def async_restore_dp_remote(self):
        _LOGGER.debug("in async_restore_dp_remote")
        entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        last_state = await entity.async_get_last_state()
        if last_state is None:
            self.set_dp_remote(1)
        elif last_state.state == 'off':
            self.set_dp_remote(0)
        elif last_state.state == 'on':
            self.set_dp_remote(1)
        else:
            self.set_dp_remote(1)
        _LOGGER.debug("out async_restore_dp_remote")

    async def async_get_firmware_version(self) -> str | None:
        """Get firmware version."""
        resp = await self.api.async_get_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_VERSION]

    async def async_get_ip_address(self) -> str | None:
        """Get device ip address."""
        resp = await self.api.async_get_wifi_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_IP_ADDRESS]
    
    async def async_get_sn_by_api(self) -> str | None:
        """Get device series number."""
        resp = await self.api.async_get_sn()
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_SN]

    async def async_set_dp(self, dp_id, status):
        if dp_id == DP_REMOTE:
            self.set_dp_remote(status)
            return
        elif dp_id == DP_LED:
            resp =  await self.api.async_set_led(self.sn, status)
        elif dp_id == DP_DEFAULT:
            resp = await self.api.async_set_default(self.sn, status)
        else:
            index = int(dp_id[-1])
            resp = await self.api.async_set_status(self.sn, index, status)

        r_json = resp.json()
        if not r_json["result"]:
            self._status.update({dp_id: status})

    async def async_set_scan_interval(self, seconds):
        if self.status('remote') or self.status('remote') is None:
            seconds = max(seconds, 60)
        else:
            seconds = max(seconds, 20)
        scan_interval = timedelta(seconds=seconds)
        self._set_scan_interval(scan_interval)
        _LOGGER.debug("in async_request_refresh")
        self.hass.async_create_task(self.update_manager.coordinator.async_request_refresh())
        _LOGGER.debug("out async_request_refresh")
        return seconds

    async def async_update(self) -> None:
        """Update the device and related entities."""
        device_registry = dr.async_get(self.hass)

        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, self.sn)}
        )
        assert device_entry
        device_registry.async_update_device(device_entry.id, sw_version=self.fw_version)
        # await self.hass.config_entries.async_reload(entry.entry_id)

    @abstractmethod
    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
    
    @abstractmethod
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""


class C1Pro(SunLoginDevice):
    """Device for C1 C1Pro C1Pro-BLE"""
    
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)

    @property
    def remote_address(self):
        return self.config.get(CONF_DEVICE_ADDRESS)
    
    @property
    def local_address(self):
        return HTTP_SUFFIX + self.config.get('ip', '0.0.0.0') + LOCAL_PORT
    
    @property
    def entities(self):
        return get_plug_entries(self.config)

    def status(self, dpid):
        # status = self.update_manager.coordinator.data
        # return status[dpid]
        return self.update_manager.coordinator.data[dpid]
    

    async def async_get_firmware_version(self) -> int | None:
        """Get firmware version."""
        resp = await self.api.async_get_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_VERSION]

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        config = self.config
        address = self.remote_address if self.remote_address else self.local_address
        api = PlugAPI(self.hass,address)
        # api.timeout = config.data[CONF_TIMEOUT]
        self.api = api


        try:
            self.fw_version = await self.async_get_firmware_version()

        except: pass
        

        update_manager = P2UpdateManager(self)
        coordinator = update_manager.coordinator
        await coordinator.async_config_entry_first_refresh()

        self.update_manager = update_manager
        self.hass.data[DOMAIN][SL_DEVICES][self.sn] = self
        # self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        
        # entities = get_device_entries(self.config)
        # await asyncio.gather(
        #     *[
        #         self.hass.config_entries.async_forward_entry_setup(entities, platform)
        #         for platform in ['switch','sensor']
        #     ]
        # )
        # await self.hass.config_entries.async_forward_entry_setups(
        #     entities, [SWITCH_DOMAIN]
        # )

        return True


class C2(SunLoginDevice):
    """Device for C2 C2-BLE"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)

    @property
    def remote_address(self):
        return self.config.get(CONF_DEVICE_ADDRESS)
    
    @property
    def local_address(self):
        return HTTP_SUFFIX + self.config.get('ip', '0.0.0.0') + LOCAL_PORT
    
    @property
    def entities(self):
        return get_device_entries(self.config)

    def status(self, dpid):
        # status = self.update_manager.coordinator.data
        # return status[dpid]
        return self.update_manager.coordinator.data[dpid]
    

    async def async_get_firmware_version(self) -> int | None:
        """Get firmware version."""
        resp = await self.api.async_get_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_VERSION]

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        config = self.config
        address = self.remote_address if self.remote_address else self.local_address
        api = PlugAPI(self.hass,address)
        # api.timeout = config.data[CONF_TIMEOUT]
        self.api = api


        try:
            self.fw_version = await self.async_get_firmware_version()

        except: pass
        

        update_manager = P2UpdateManager(self)
        coordinator = update_manager.coordinator
        await coordinator.async_config_entry_first_refresh()

        self.update_manager = update_manager
        self.hass.data[DOMAIN].devices[config.entry_id] = self
        self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        
        # entities = get_device_entries(self.config)
        # await asyncio.gather(
        #     *[
        #         self.hass.config_entries.async_forward_entry_setup(entities, platform)
        #         for platform in ['switch','sensor']
        #     ]
        # )
        # await self.hass.config_entries.async_forward_entry_setups(
        #     entities, [SWITCH_DOMAIN]
        # )

        return True

class P1Pro(SunLoginDevice):
    """Device for P1 P1Pro"""

    _ip = None
    new_data = dict()

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        # self._memos = get_plug_memos(self.config)
        self._status = {}
        self.update_manager = P1UpdateManager(self)

    @property
    def remote_address(self):
        return self.config.get(CONF_DEVICE_ADDRESS)
    
    @property
    def local_address(self):
        if self._ip is not None: 
            return HTTP_SUFFIX + self._ip + LOCAL_PORT
        elif (ip := self.config.get('ip')) is not None:
            return HTTP_SUFFIX + ip + LOCAL_PORT
    
    @property
    def entities(self):
        return get_plug_entries(self.config)

    @property
    def memos(self):
        return get_plug_memos(self.config)
    
    def status(self, dp_id):
        # status = self.update_manager.coordinator.data
        # return status[dpid]
        return self._status.get(dp_id)
        # return self.update_manager.coordinator.data[dpid]
    
    def set_dp_remote(self, status):
        _LOGGER.debug(self.remote_address)
        _LOGGER.debug(self.local_address)
        if status is None:
            return
        elif status and self.remote_address is not None:
            # self.api = PlugAPI(self.hass, self.remote_address)
            self.api.address = self.remote_address
            self._status.update({DP_REMOTE: status})
        elif not status and self.local_address is not None:
            # self.api = PlugAPI(self.hass, self.local_address)
            self.api.address = self.local_address
            self._status.update({DP_REMOTE: status})
        # store dp_remote status
        # entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        # async_get(self.hass).async_restore_entity_added(entity)

    def get_entity(self, unique_id):
        for entity in self._entities:
            if unique_id == entity.unique_id:
                return entity
            
    def get_sn_by_configuration(self):
        return self.config.get(CONF_DEVICE_SN)
    
    def update_configuration(self):
        if len(self.new_data) > 0:
            try:
                update_device_configuration(self.hass, self.get_sn_by_configuration(), self.new_data)
                self.new_data = dict()
            except:
                _LOGGER.debug('update_device_configuration failed')
        
    async def async_restore_dp_remote(self):
        _LOGGER.debug("in async_restore_dp_remote")
        entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        last_state = await entity.async_get_last_state()
        if last_state is None:
            self.set_dp_remote(1)
        elif last_state.state == 'off':
            self.set_dp_remote(0)
        elif last_state.state == 'on':
            self.set_dp_remote(1)
        else:
            self.set_dp_remote(1)
        _LOGGER.debug("out async_restore_dp_remote")

    async def async_restore_electricity(self):
        _LOGGER.debug("in async_restore_electricity")
        for dp_id in [DP_ELECTRICITY_HOUR, DP_ELECTRICITY_DAY, DP_ELECTRICITY_WEEK, DP_ELECTRICITY_MONTH, DP_ELECTRICITY_LASTMONTH]:
            entity = self.get_entity(f"sunlogin_{self.sn}_{dp_id}")
            last_state = await entity.async_get_last_state()
            if last_state is not None:
                self._status.update({dp_id: last_state.state})
                    
        _LOGGER.debug("out async_restore_electricity")

    async def async_set_scan_interval(self, seconds):
        if self.status('remote') or self.status('remote') is None:
            seconds = max(seconds, 60)
        else:
            seconds = max(seconds, 20)
        scan_interval = timedelta(seconds=seconds)
        self._set_scan_interval(scan_interval)
        _LOGGER.debug("in async_request_refresh")
        self.hass.async_create_task(self.update_manager.coordinator.async_request_refresh())
        _LOGGER.debug("out async_request_refresh")
        return seconds

    async def async_set_dp(self, dp_id, status):
        if dp_id == DP_REMOTE:
            self.set_dp_remote(status)
            return
        elif dp_id == DP_LED:
            resp =  await self.api.async_set_led(self.sn, status)
        elif dp_id == DP_DEFAULT:
            resp = await self.api.async_set_default(self.sn, status)
        else:
            index = int(dp_id[-1])
            resp = await self.api.async_set_status(self.sn, index, status)

        r_json = resp.json()
        if not r_json["result"]:
            self._status.update({dp_id: status})

    async def async_get_firmware_version(self) -> str | None:
        """Get firmware version."""
        resp = await self.api.async_get_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_VERSION]

    async def async_get_ip_address(self) -> str | None:
        """Get device ip address."""
        resp = await self.api.async_get_wifi_info(self.sn)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_IP_ADDRESS]
    
    async def async_get_sn_by_api(self) -> str | None:
        """Get device series number."""
        resp = await self.api.async_get_sn()
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_SN]

    async def async_update(self) -> None:
        """Update the device and related entities."""
        device_registry = dr.async_get(self.hass)

        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, self.sn)}
        )
        assert device_entry
        device_registry.async_update_device(device_entry.id, sw_version=self.fw_version)
        # await self.hass.config_entries.async_reload(entry.entry_id)

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        address = self.remote_address if self.remote_address else self.local_address
        api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        self.api = api

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            try:
                self.sn = await self.async_get_sn_by_api()
                self.new_data[CONF_DEVICE_SN] = self.sn
            except:
                pass
        
        if self.remote_address:
            try:
                self._ip = await self.async_get_ip_address()
                self.new_data[CONF_DEVICE_IP_ADDRESS] = self._ip
            except:
                pass
            await self.async_restore_dp_remote()

        try:
            self.fw_version = await self.async_get_firmware_version()
            self.new_data[CONF_DEVICE_VERSION] = self.fw_version
        except: 
            if (version := self.config.get(CONF_DEVICE_VERSION)) is not None:
                self.fw_version = version
        _LOGGER.debug("new_data %s",self.new_data)        
        _LOGGER.debug(self.local_address)
        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        coordinator.update_interval = self.update_manager.UPDATE_INTERVAL
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        await coordinator.async_config_entry_first_refresh()

        # self.update_manager = update_manager
        # self.hass.data[DOMAIN][SL_DEVICES][self.sn] = self
        # self.reset_jobs.append(config.add_update_listener(self.async_update))
        # Forward entry setup to related domains.
        
        # entities = get_device_entries(self.config)
        # await asyncio.gather(
        #     *[
        #         self.hass.config_entries.async_forward_entry_setup(entities, platform)
        #         for platform in ['switch','sensor']
        #     ]
        # )
        # await self.hass.config_entries.async_forward_entry_setups(
        #     entities, [SWITCH_DOMAIN]
        # )
        await self.async_update()
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        




class SunloginUpdateManager(ABC):
    """Representation of a Broadlink update manager.

    Implement this class to manage fetching data from the device and to
    monitor device availability.
    """
    UPDATE_COUNT = 0
    UPDATE_INTERVAL = timedelta(seconds=60)
    FIRST_UPDATE_INTERVAL = timedelta(seconds=10)
    

    def __init__(self, device):
        """Initialize the update manager."""
        self.device = device
        # self.SCAN_INTERVAL = timedelta(seconds=scan_interval)
        self.coordinator = DataUpdateCoordinator(
            device.hass,
            _LOGGER,
            name=f"{device.name} ({device.model} at {device.sn})",
            update_method=self.async_update,
            update_interval=self.UPDATE_INTERVAL,
        )
        self.available = None
        self.last_update = None

    async def async_update(self):
        """Fetch data from the device and update availability."""
        try:
            data = await self.async_fetch_data()

        except Exception as err:
            if self.available and (
                dt_util.utcnow() - self.last_update > self.SCAN_INTERVAL * 3
            ):
                self.available = False
                _LOGGER.warning(
                    "Disconnected from %s (%s at %s)",
                    self.device.name,
                    self.device.api.model,
                    self.device.api.host[0],
                )
            raise UpdateFailed(err) from err

        if self.available is False:
            _LOGGER.warning(
                "Connected to %s (%s at %s)",
                self.device.name,
                self.device.model,
                self.device.sn,
            )
        self.available = True
        self.last_update = dt_util.utcnow()
        return data

    @abstractmethod
    async def async_fetch_data(self):
        """Fetch data from the device."""

class PlugConfigUpdateManager(SunloginUpdateManager):

    UPDATE_INTERVAL = timedelta(hours=1)
    devices = list()

    def __init__(self, hass):
        """Initialize the update manager."""
        self.hass = hass
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Config Update (Plug at 0x0001)",
            update_method=self.async_update,
            update_interval=self.UPDATE_INTERVAL,
        )
        self.available = None
        self.last_update = None

        self.coordinator.async_add_listener(self.nop)

    # def add_listener(self):
    #     self.coordinator.async_add_listener(self.nop)

    def nop(self):
        ''''''

    async def async_fetch_data(self):
        """Fetch data from the device."""
        for device in self.devices:
            device.update_configuration()
            _LOGGER.debug(f"{device.name} ({device.sn})")

class P2UpdateManager(SunloginUpdateManager):
    "Plug without electric"

    async def async_fetch_data(self):
        """Fetch data from the device."""
        sn = self.device.sn
        api = self.device.api
        status = {}
        if value := self.coordinator.data is not None:
            status.update(value)
        try:
            resp = await api.async_get_status(sn)
            r_json = resp.json()
            status.update(plug_status_process(r_json))
        except: pass

class P1UpdateManager(SunloginUpdateManager):
    "Plug with electric"

    last_power_consumes_update = datetime.fromtimestamp(0, timezone.utc)

    async def async_fetch_data(self):
        """Fetch data from the device."""
        sn = self.device.sn
        api = self.device.api
        status = self.device._status
        # if value := self.coordinator.data is not None:
        #     status.update(value)
        try:
            resp = await api.async_get_electric(sn)
            _LOGGER.debug(resp.text)
            r_json = resp.json()
            status.update(plug_electric_process(r_json))
        except: pass

        try:
            resp = await api.async_get_status(sn)
            _LOGGER.debug(resp.text)
            r_json = resp.json()
            status.update(plug_status_process(r_json))
        except: pass

        if self.device.remote_address and dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
            try:
                resp = await api.async_get_power_consumes(sn)
                # _LOGGER.debug(resp.text)
                r_json = resp.json()
                status.update(plug_power_consumes_process(r_json))
                self.last_power_consumes_update = dt_util.utcnow()
            except: pass
        
        # if self.UPDATE_COUNT % 2 == 1:
        #     self.device.update_configuration()
        _LOGGER.debug(self.device._status)

        self.UPDATE_COUNT += 1
        return status

class Token():
    access_token = None
    refresh_token = None
    create_time = None
    coordinator = None
    _api_v1 = None
    _api_v2 = None
    interval = 600
    
    def __init__(self, hass):
        self.hass = hass
        self.refresh_expire = 0
        self.refresh_ttl = timedelta(seconds=200)

    def setup(self, access_token, refresh_token, create_time):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.create_time = create_time
        self.refresh_expire = create_time + 30*24*3600 - 60
        self.coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=f"Token Update (access_token at {self.create_time})",
            update_method=self.async_update,
            update_interval=self.refresh_ttl,
        )
        self.coordinator.async_add_listener(self.nop)
        self.setup_api()

    def setup_by_json(self, token_json):
        access_token = token_json.get(CONF_ACCESS_TOKEN, 'a')
        refresh_token = token_json.get(CONF_REFRESH_TOKEN, 'r')
        create_time = token_json.get(CONF_REFRESH_EXPIRE, time.time()+30*24*3600) - 30*24*3600
        # create_time = time.time()
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.create_time = create_time
        self.refresh_expire = create_time + 30*24*3600 - 60
        self.coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=f"Token Update (access_token at {self.create_time})",
            update_method=self.async_update,
            update_interval=self.refresh_ttl,
        )
        self.coordinator.async_add_listener(self.nop)
        self.setup_api()

    def setup_api(self):
        self._api_v1 = CloudAPI(self.hass)
        self._api_v2 = CloudAPI_V2(self.hass)

    def nop(self):
        ''''''

    def check(self):
        if self.access_token == 'a' or self.refresh_token == 'r' or time.time() > self.refresh_expire:
            return False
        return True

    def need_update(self):
        info = toekn_decode(self.access_token)
        exp = info.get('exp', 0)
        if time.time() >= exp:
            return True
        return False

    async def async_update(self):
        if not self.check():
            return
        
        if not self.need_update() and time.time() - self.create_time < self.interval:
            return False
        
        new_token = await self.async_update_by_refresh_token()

        if new_token is not None:
            self.access_token = new_token[CONF_ACCESS_TOKEN]
            self.refresh_token = new_token[CONF_REFRESH_TOKEN]
            self.create_time = new_token.get(CONF_REFRESH_EXPIRE, time.time()+30*24*3600) - 30*24*3600
            #store token
            entry = config_entries.current_entry.get()
            new_data = {**entry.data}
            new_data[CONF_ACCESS_TOKEN] = self.access_token
            new_data[CONF_REFRESH_TOKEN] = self.refresh_token
            new_data[CONF_REFRESH_EXPIRE] = self.create_time
            self.hass.config_entries.async_update_entry(entry, data=new_data)

        return True
        
    async def async_update_by_refresh_token(self):
        ''''''
        _LOGGER.debug('in async_update_by_refresh_token')
        error, resp = await async_request_error_process(self._api_v1.async_refresh_token, self.access_token, self.refresh_token)

        if error is not None:
            _LOGGER.debug(error)
            return None
        
        r_json = resp.json()
        return r_json

    async def async_update_by_session(self):
        ''''''


class PlugAPI():
    VERSION = 2

    def __init__(self, hass, address):
        self.hass = hass
        self.token = get_current_token(hass)
        self._api = PlugAPI_V2(hass, self.process_address(address))

    @property
    def address(self):
        return self._api.address
    
    @address.setter
    def address(self, address):
        self._api.address = self.process_address(address)

    @property
    def timeout(self):
        return self._api.timeout
    
    @timeout.setter
    def timeout(self, timeout):
        self._api.timeout = timeout

    def process_address(self, address):
        if self.VERSION == 2 and address[-4:] == '8000':
            address = 'https://slapi.oray.net'
        return address

    async def async_get_status(self, sn):
        return await self._api.async_get_status(sn, self.token.access_token)
    
    async def async_get_electric(self, sn):
        return await self._api.async_get_electric(sn, self.token.access_token)
    
    async def async_get_info(self, sn):
        return await self._api.async_get_info(sn, self.token.access_token)
    
    async def async_get_sn(self, sn='sunlogin'):
        return await self._api.async_get_sn(sn, self.token.access_token)
    
    async def async_get_wifi_info(self, sn):
        return await self._api.async_get_wifi_info(sn, self.token.access_token)
    
    async def async_set_status(self, sn, index, status):
        return await self._api.async_set_status(sn, self.token.access_token, index, status)

    async def async_set_led(self, sn, status):
        return await self._api.async_set_led(sn, self.token.access_token, status)

    async def async_set_default(self, sn, status):
        return await self._api.async_set_default(sn, self.token.access_token, status)

    async def async_get_power_consumes(self, sn):
        return await self._api.async_get_power_consumes(sn)
    
