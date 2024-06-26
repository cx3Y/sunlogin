import functools
import hashlib
import json
import logging
import time
import uuid
import math
import base64
import asyncio
import requests
import async_timeout
import aiohttp
from .sunlogin_api import CloudAPI, CloudAPI_V2, PlugAPI_V1, PlugAPI_V2
# from .fake_data import GET_PLUG_ELECTRIC_FAKE_DATA_P8, GET_PLUG_STATUS_FAKE_DATA_P8
from .dns_api import DNS
# from .sunlogin_api import PlugAPI_V2 as PlugAPI
from datetime import timedelta, datetime, timezone

from abc import ABC, abstractmethod
from urllib.parse import urlencode
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.restore_state import async_get
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed
)
from homeassistant.util import dt as dt_util
from homeassistant.const import (
    CONF_UNIT_OF_MEASUREMENT,
    CONF_PLATFORM,
    CONF_DEVICES,
)
from homeassistant import config_entries

from .const import (
    DOMAIN,
    PLUG_DOMAIN,
    PLUG_URL,
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
    CONF_DNS_UPDATE,
    HTTP_SUFFIX, 
    LOCAL_PORT,
)


_LOGGER = logging.getLogger(__name__)

UPDATE_FLAG_SN = 'update_flag_sn'
UPDATE_FLAG_IP = 'update_flag_ip'
UPDATE_FLAG_VERSION = 'update_flag_version'

ELECTRIC_MODEL = ["C1-2", "C2", "C2_BLE", "C2-BLE", "P1", "P1Pro", "P4", "P8", "P8Pro"]   #, "SunLogin generic"
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
DP_SUB_POWER_0 = "sub_power0"
DP_SUB_POWER_1 = "sub_power1"
DP_SUB_POWER_2 = "sub_power2"
DP_SUB_POWER_3 = "sub_power3"
DP_SUB_POWER_4 = "sub_power4"
DP_SUB_POWER_5 = "sub_power5"
DP_SUB_POWER_6 = "sub_power6"
DP_SUB_POWER_7 = "sub_power7"
DP_SUB_CURRENT_0 = "sub_current0"
DP_SUB_CURRENT_1 = "sub_current1"
DP_SUB_CURRENT_2 = "sub_current2"
DP_SUB_CURRENT_3 = "sub_current3"
DP_SUB_CURRENT_4 = "sub_current4"
DP_SUB_CURRENT_5 = "sub_current5"
DP_SUB_CURRENT_6 = "sub_current6"
DP_SUB_CURRENT_7 = "sub_current7"
DP_SUB_ELECTRICITY_HOUR_0 = "sub_electricity_hour0"
DP_SUB_ELECTRICITY_HOUR_1 = "sub_electricity_hour1"
DP_SUB_ELECTRICITY_HOUR_2 = "sub_electricity_hour2"
DP_SUB_ELECTRICITY_HOUR_3 = "sub_electricity_hour3"
DP_SUB_ELECTRICITY_HOUR_4 = "sub_electricity_hour4"
DP_SUB_ELECTRICITY_HOUR_5 = "sub_electricity_hour5"
DP_SUB_ELECTRICITY_HOUR_6 = "sub_electricity_hour6"
DP_SUB_ELECTRICITY_HOUR_7 = "sub_electricity_hour7"
DP_SUB_ELECTRICITY_DAY_0 = "sub_electricity_day0"
DP_SUB_ELECTRICITY_DAY_1 = "sub_electricity_day1"
DP_SUB_ELECTRICITY_DAY_2 = "sub_electricity_day2"
DP_SUB_ELECTRICITY_DAY_3 = "sub_electricity_day3"
DP_SUB_ELECTRICITY_DAY_4 = "sub_electricity_day4"
DP_SUB_ELECTRICITY_DAY_5 = "sub_electricity_day5"
DP_SUB_ELECTRICITY_DAY_6 = "sub_electricity_day6"
DP_SUB_ELECTRICITY_DAY_7 = "sub_electricity_day7"
DP_SUB_ELECTRICITY_WEEK_0 = "sub_electricity_week0"
DP_SUB_ELECTRICITY_WEEK_1 = "sub_electricity_week1"
DP_SUB_ELECTRICITY_WEEK_2 = "sub_electricity_week2"
DP_SUB_ELECTRICITY_WEEK_3 = "sub_electricity_week3"
DP_SUB_ELECTRICITY_WEEK_4 = "sub_electricity_week4"
DP_SUB_ELECTRICITY_WEEK_5 = "sub_electricity_week5"
DP_SUB_ELECTRICITY_WEEK_6 = "sub_electricity_week6"
DP_SUB_ELECTRICITY_WEEK_7 = "sub_electricity_week7"
DP_SUB_ELECTRICITY_MONTH_0 = "sub_electricity_month0"
DP_SUB_ELECTRICITY_MONTH_1 = "sub_electricity_month1"
DP_SUB_ELECTRICITY_MONTH_2 = "sub_electricity_month2"
DP_SUB_ELECTRICITY_MONTH_3 = "sub_electricity_month3"
DP_SUB_ELECTRICITY_MONTH_4 = "sub_electricity_month4"
DP_SUB_ELECTRICITY_MONTH_5 = "sub_electricity_month5"
DP_SUB_ELECTRICITY_MONTH_6 = "sub_electricity_month6"
DP_SUB_ELECTRICITY_MONTH_7 = "sub_electricity_month7"
DP_SUB_ELECTRICITY_LASTMONTH_0 = "sub_electricity_lastmonth0"
DP_SUB_ELECTRICITY_LASTMONTH_1 = "sub_electricity_lastmonth1"
DP_SUB_ELECTRICITY_LASTMONTH_2 = "sub_electricity_lastmonth2"
DP_SUB_ELECTRICITY_LASTMONTH_3 = "sub_electricity_lastmonth3"
DP_SUB_ELECTRICITY_LASTMONTH_4 = "sub_electricity_lastmonth4"
DP_SUB_ELECTRICITY_LASTMONTH_5 = "sub_electricity_lastmonth5"
DP_SUB_ELECTRICITY_LASTMONTH_6 = "sub_electricity_lastmonth6"
DP_SUB_ELECTRICITY_LASTMONTH_7 = "sub_electricity_lastmonth7"

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
    DP_SUB_POWER_0: "sensor",
    DP_SUB_POWER_1: "sensor",
    DP_SUB_POWER_2: "sensor",
    DP_SUB_POWER_3: "sensor",
    DP_SUB_POWER_4: "sensor",
    DP_SUB_POWER_5: "sensor",
    DP_SUB_POWER_6: "sensor",
    DP_SUB_POWER_7: "sensor",
    DP_SUB_CURRENT_0: "sensor",
    DP_SUB_CURRENT_1: "sensor",
    DP_SUB_CURRENT_2: "sensor",
    DP_SUB_CURRENT_3: "sensor",
    DP_SUB_CURRENT_4: "sensor",
    DP_SUB_CURRENT_5: "sensor",
    DP_SUB_CURRENT_6: "sensor",
    DP_SUB_CURRENT_7: "sensor",
    DP_SUB_ELECTRICITY_HOUR_0: "sensor",
    DP_SUB_ELECTRICITY_HOUR_1: "sensor",
    DP_SUB_ELECTRICITY_HOUR_2: "sensor",
    DP_SUB_ELECTRICITY_HOUR_3: "sensor",
    DP_SUB_ELECTRICITY_HOUR_4: "sensor",
    DP_SUB_ELECTRICITY_HOUR_5: "sensor",
    DP_SUB_ELECTRICITY_HOUR_6: "sensor",
    DP_SUB_ELECTRICITY_HOUR_7: "sensor",
    DP_SUB_ELECTRICITY_DAY_0: "sensor",
    DP_SUB_ELECTRICITY_DAY_1: "sensor",
    DP_SUB_ELECTRICITY_DAY_2: "sensor",
    DP_SUB_ELECTRICITY_DAY_3: "sensor",
    DP_SUB_ELECTRICITY_DAY_4: "sensor",
    DP_SUB_ELECTRICITY_DAY_5: "sensor",
    DP_SUB_ELECTRICITY_DAY_6: "sensor",
    DP_SUB_ELECTRICITY_DAY_7: "sensor",
    DP_SUB_ELECTRICITY_WEEK_0: "sensor",
    DP_SUB_ELECTRICITY_WEEK_1: "sensor",
    DP_SUB_ELECTRICITY_WEEK_2: "sensor",
    DP_SUB_ELECTRICITY_WEEK_3: "sensor",
    DP_SUB_ELECTRICITY_WEEK_4: "sensor",
    DP_SUB_ELECTRICITY_WEEK_5: "sensor",
    DP_SUB_ELECTRICITY_WEEK_6: "sensor",
    DP_SUB_ELECTRICITY_WEEK_7: "sensor",
    DP_SUB_ELECTRICITY_MONTH_0: "sensor",
    DP_SUB_ELECTRICITY_MONTH_1: "sensor",
    DP_SUB_ELECTRICITY_MONTH_2: "sensor",
    DP_SUB_ELECTRICITY_MONTH_3: "sensor",
    DP_SUB_ELECTRICITY_MONTH_4: "sensor",
    DP_SUB_ELECTRICITY_MONTH_5: "sensor",
    DP_SUB_ELECTRICITY_MONTH_6: "sensor",
    DP_SUB_ELECTRICITY_MONTH_7: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_0: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_1: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_2: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_3: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_4: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_5: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_6: "sensor",
    DP_SUB_ELECTRICITY_LASTMONTH_7: "sensor",
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
EXTRA_ENTITY_P8 = [
    DP_SUB_POWER_0,
    DP_SUB_POWER_1,
    DP_SUB_POWER_2,
    DP_SUB_POWER_3,
    DP_SUB_POWER_4,
    DP_SUB_POWER_5,
    DP_SUB_POWER_6,
    DP_SUB_POWER_7,
    DP_SUB_CURRENT_0,
    DP_SUB_CURRENT_1,
    DP_SUB_CURRENT_2,
    DP_SUB_CURRENT_3,
    DP_SUB_CURRENT_4,
    DP_SUB_CURRENT_5,
    DP_SUB_CURRENT_6,
    DP_SUB_CURRENT_7,
    DP_SUB_ELECTRICITY_HOUR_0,
    DP_SUB_ELECTRICITY_HOUR_1,
    DP_SUB_ELECTRICITY_HOUR_2,
    DP_SUB_ELECTRICITY_HOUR_3,
    DP_SUB_ELECTRICITY_HOUR_4,
    DP_SUB_ELECTRICITY_HOUR_5,
    DP_SUB_ELECTRICITY_HOUR_6,
    DP_SUB_ELECTRICITY_HOUR_7,
    DP_SUB_ELECTRICITY_DAY_0,
    DP_SUB_ELECTRICITY_DAY_1,
    DP_SUB_ELECTRICITY_DAY_2,
    DP_SUB_ELECTRICITY_DAY_3,
    DP_SUB_ELECTRICITY_DAY_4,
    DP_SUB_ELECTRICITY_DAY_5,
    DP_SUB_ELECTRICITY_DAY_6,
    DP_SUB_ELECTRICITY_DAY_7,
    DP_SUB_ELECTRICITY_WEEK_0,
    DP_SUB_ELECTRICITY_WEEK_1,
    DP_SUB_ELECTRICITY_WEEK_2,
    DP_SUB_ELECTRICITY_WEEK_3,
    DP_SUB_ELECTRICITY_WEEK_4,
    DP_SUB_ELECTRICITY_WEEK_5,
    DP_SUB_ELECTRICITY_WEEK_6,
    DP_SUB_ELECTRICITY_WEEK_7,
    DP_SUB_ELECTRICITY_MONTH_0,
    DP_SUB_ELECTRICITY_MONTH_1,
    DP_SUB_ELECTRICITY_MONTH_2,
    DP_SUB_ELECTRICITY_MONTH_3,
    DP_SUB_ELECTRICITY_MONTH_4,
    DP_SUB_ELECTRICITY_MONTH_5,
    DP_SUB_ELECTRICITY_MONTH_6,
    DP_SUB_ELECTRICITY_MONTH_7,
    DP_SUB_ELECTRICITY_LASTMONTH_0,
    DP_SUB_ELECTRICITY_LASTMONTH_1,
    DP_SUB_ELECTRICITY_LASTMONTH_2,
    DP_SUB_ELECTRICITY_LASTMONTH_3,
    DP_SUB_ELECTRICITY_LASTMONTH_4,
    DP_SUB_ELECTRICITY_LASTMONTH_5,
    DP_SUB_ELECTRICITY_LASTMONTH_6,
    DP_SUB_ELECTRICITY_LASTMONTH_7,
]
ELECTRIC_ENTITY = [DP_ELECTRICITY_HOUR, DP_ELECTRICITY_DAY, DP_ELECTRICITY_WEEK, DP_ELECTRICITY_MONTH, DP_ELECTRICITY_LASTMONTH, DP_POWER, DP_CURRENT, DP_VOLTAGE]
SLOT_X_WITHOUT_ELECTRIC = [DP_LED, DP_DEFAULT, DP_RELAY_0, DP_RELAY_1, DP_RELAY_2, DP_RELAY_3, DP_RELAY_4, DP_RELAY_5, DP_RELAY_6, DP_RELAY_7]
SLOT_X_WITH_ELECTRIC = ELECTRIC_ENTITY + SLOT_X_WITHOUT_ELECTRIC


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
        return P2(hass, config)
    elif 'P4' in model:
        return P4(hass, config)
    elif 'P8' in model:
        return P8(hass, config)
    else:
        pass

async def guess_model(hass, ip):
    model = None
    sn = None
    local_address = HTTP_SUFFIX + ip + LOCAL_PORT
    plug_api = PlugAPI_V1(hass, local_address)

    resp_sn = await plug_api.async_get_sn()
    sn = resp_sn.json()[CONF_DEVICE_SN]
    try:
        resp_electric = await plug_api.async_get_electric(sn)
        check_electric = resp_electric.json()['result']
    except: pass

    try:
        resp_state = await plug_api.async_get_status(sn)
        check_slot = len(resp_state.json()['response'])
    except: pass

    if check_electric == 0: #support electric
        if check_slot == 1:
            model = 'C2'
        elif check_slot == 3:
            model = 'P4'
        elif check_slot == 4:
            model = 'P1Pro'
        elif check_slot == 8:
            model = 'P8Pro'
    else:
        if check_slot == 1:
            model = 'C1Pro'
        elif check_slot == 3:
            model = 'P2'
    
    return sn, model

def get_plug_entries(config):
    model = config.get(CONF_DEVICE_MODEL) 
    entities = dict()

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
    memos = dict()
    model = config.get(CONF_DEVICE_MODEL)

    for item in config.get(CONF_DEVICE_MEMOS, []):
        index = item.get('number', 0)
        name = item.get('name')
        if name is not None:
            memos.update({f'relay{index}': name})
            if 'P8' in model:
                memos.update({f'sub_power{index}': name})
                memos.update({f'sub_current{index}': name})
                memos.update({f'sub_electricity_hour{index}': name})
                memos.update({f'sub_electricity_day{index}': name})
                memos.update({f'sub_electricity_week{index}': name})
                memos.update({f'sub_electricity_month{index}': name})
                memos.update({f'sub_electricity_lastmonth{index}': name})

    return memos
    

def plug_status_process(data):
    status = dict()
    for relay_status in data.get(DP_RELAY, ''):
        index = relay_status['index']
        value = relay_status['status']
        power = relay_status.get('power') #P8 series only
        status[f"relay{index}"]= value

    if (led := data.get(DP_LED)) is not None:
        status[DP_LED] = led
    
    if (default := data.get(DP_DEFAULT)) is not None:
        status[DP_DEFAULT] = default

    return status

def plug_electric_process(data):
    status = dict()
    if (voltage := data.get('vol')) is not None:
        status[DP_VOLTAGE] = voltage

    if (current := data.get('curr')) is not None:
        current = current // 1000
        status[DP_CURRENT] = current

    if (power := data.get('power')) is not None:
        power = power / 1000
        status[DP_POWER] = power
    
    if (sub_electric := data.get('sub')) is not None:
        for index, electric in enumerate(sub_electric):
            sub_current = electric['cur']
            sub_current = sub_current // 1000
            sub_power = electric['pwr']
            sub_power = sub_power / 1000
            status[f"sub_current{index}"] = sub_current
            status[f"sub_power{index}"] = sub_power

    return status

def plug_power_consumes_process(data, index=0):
    status = dict()
    dp_electricity_hour = [DP_ELECTRICITY_HOUR,DP_SUB_ELECTRICITY_HOUR_0,DP_SUB_ELECTRICITY_HOUR_1,DP_SUB_ELECTRICITY_HOUR_2,DP_SUB_ELECTRICITY_HOUR_3,DP_SUB_ELECTRICITY_HOUR_4,DP_SUB_ELECTRICITY_HOUR_5,DP_SUB_ELECTRICITY_HOUR_6,DP_SUB_ELECTRICITY_HOUR_7][index]
    dp_electricity_day = [DP_ELECTRICITY_DAY,DP_SUB_ELECTRICITY_DAY_0,DP_SUB_ELECTRICITY_DAY_1,DP_SUB_ELECTRICITY_DAY_2,DP_SUB_ELECTRICITY_DAY_3,DP_SUB_ELECTRICITY_DAY_4,DP_SUB_ELECTRICITY_DAY_5,DP_SUB_ELECTRICITY_DAY_6,DP_SUB_ELECTRICITY_DAY_7][index]
    dp_electricity_week = [DP_ELECTRICITY_WEEK,DP_SUB_ELECTRICITY_WEEK_0,DP_SUB_ELECTRICITY_WEEK_1,DP_SUB_ELECTRICITY_WEEK_2,DP_SUB_ELECTRICITY_WEEK_3,DP_SUB_ELECTRICITY_WEEK_4,DP_SUB_ELECTRICITY_WEEK_5,DP_SUB_ELECTRICITY_WEEK_6,DP_SUB_ELECTRICITY_WEEK_7][index]
    dp_electricity_month = [DP_ELECTRICITY_MONTH,DP_SUB_ELECTRICITY_MONTH_0,DP_SUB_ELECTRICITY_MONTH_1,DP_SUB_ELECTRICITY_MONTH_2,DP_SUB_ELECTRICITY_MONTH_3,DP_SUB_ELECTRICITY_MONTH_4,DP_SUB_ELECTRICITY_MONTH_5,DP_SUB_ELECTRICITY_MONTH_6,DP_SUB_ELECTRICITY_MONTH_7][index]
    dp_electricity_lastmonth = [DP_ELECTRICITY_LASTMONTH,DP_SUB_ELECTRICITY_LASTMONTH_0,DP_SUB_ELECTRICITY_LASTMONTH_1,DP_SUB_ELECTRICITY_LASTMONTH_2,DP_SUB_ELECTRICITY_LASTMONTH_3,DP_SUB_ELECTRICITY_LASTMONTH_4,DP_SUB_ELECTRICITY_LASTMONTH_5,DP_SUB_ELECTRICITY_LASTMONTH_6,DP_SUB_ELECTRICITY_LASTMONTH_7][index]
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
            status[dp_electricity_hour] = Hour
        if Day > 0:
            status[dp_electricity_day] = Day
        if Week > 0:
            status[dp_electricity_week] = Week
        if Month > 0:
            status[dp_electricity_month] = Month
        if LastMonth - Month > 0:
            status[dp_electricity_lastmonth] = LastMonth - Month

    return status

def get_current_token(hass):
    entry_id = config_entries.current_entry.get().entry_id
    token = hass.data[DOMAIN][CONFIG][entry_id][CONF_TOKEN]
    return token

def toekn_decode(access_token):
    if not access_token or access_token == 'a':
        return dict()
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
        self.userid = toekn_decode(self.access_token).get('uid')

        return "ok"

    async def async_get_access_token_by_sms(self, username, smscode):

        error, resp = await async_request_error_process(self._api_v1.async_login_by_sms, username, smscode)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.access_token = r_json.get(CONF_ACCESS_TOKEN, '')
        self.refresh_token = r_json.get(CONF_REFRESH_TOKEN, '')
        self.refresh_expire = time.time()
        self.userid = toekn_decode(self.access_token).get('uid')

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
    _entities = None
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


class SunloginPlug(SunLoginDevice, ABC):
    
    _ip = None
    _status = None
    new_data = None
    update_manager = None
    update_flag = None
    
    @property
    def remote_address(self):
        return self.config.get(CONF_DEVICE_ADDRESS)
    
    @property
    def local_address(self):
        if self._ip is not None: 
            return HTTP_SUFFIX + self._ip + LOCAL_PORT
        elif (ip := self.config.get(CONF_DEVICE_IP_ADDRESS)) is not None:
            return HTTP_SUFFIX + ip + LOCAL_PORT
    
    @property
    def default_address(self):
        address = self.remote_address if self.remote_address else self.local_address
        return address

    def status(self, dp_id):
        return self._status.get(dp_id)
    
    def available(self, dp_id):
        if dp_id == DP_REMOTE:
            if self.status(dp_id) is not None and self._ip is not None and self.remote_address is not None:
                return True
            else: 
                return False
        return self.update_manager.available
    
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
        
        # entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        # _LOGGER.debug(entity)
        # entity.async_write_ha_state()

    def get_sersor_remark(self, dp_id):
        return None

    def get_entity(self, unique_id):
        for entity in self._entities:
            if unique_id == entity.unique_id:
                return entity
            
    def get_sn_by_configuration(self):
        return self.config.get(CONF_DEVICE_SN)
    
    def update_configuration(self):
        if len(self.new_data) > 0:
            _LOGGER.debug('update_device_configuration')
            try:
                update_device_configuration(self.hass, self.get_sn_by_configuration(), self.new_data)
                self.new_data = dict()
            except:
                _LOGGER.debug('update_device_configuration failed')

    def pop_update_flag(self, flag):
        for index, _flag in enumerate(self.update_flag):
            if _flag == flag:
                self.update_flag.pop(index)
                break
        
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
            seconds = max(seconds, 10)
        scan_interval = timedelta(seconds=seconds)
        self.coordinator.update_interval = scan_interval
        self.coordinator.async_set_updated_data(data=self._status)
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

    async def async_update_sn(self):
        try:
            self.sn = await self.async_get_sn_by_api()
            self.new_data[CONF_DEVICE_SN] = self.sn
            self.pop_update_flag(UPDATE_FLAG_SN)
        except:
            pass

    async def async_update_ip(self):
        try:
            self._ip = await self.async_get_ip_address()
            self.new_data[CONF_DEVICE_IP_ADDRESS] = self._ip
            self.pop_update_flag(UPDATE_FLAG_IP)
        except:
            pass
    
    async def async_update_fw_version(self):
        try:
            self.fw_version = await self.async_get_firmware_version()
            self.new_data[CONF_DEVICE_VERSION] = self.fw_version
            self.pop_update_flag(UPDATE_FLAG_VERSION)
            await self.async_update()
        except: 
            if (version := self.config.get(CONF_DEVICE_VERSION)) is not None:
                self.fw_version = version

    @abstractmethod
    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
    
    @abstractmethod
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""


class C1Pro(SunloginPlug):
    """Device for C1 C1Pro C1Pro-BLE"""
    
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P2UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITHOUT_ELECTRIC.copy()
        entities = entities[:-7]
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return dict()

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)
        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        # try:
        #     await coordinator.async_config_entry_first_refresh()
        # except: pass
        await self.async_update()
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""

class P2(SunloginPlug):
    """Device for P2"""
    
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P2UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITHOUT_ELECTRIC.copy()
        entities = entities[:-5]
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return dict()

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)
        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        # try:
        #     await coordinator.async_config_entry_first_refresh()
        # except: pass
        await self.async_update()
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""



class C2(SunloginPlug):
    """Device for C2 C2-BLE"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P1UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITH_ELECTRIC.copy()
        entities = entities[:-7]
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return dict()
    
    async def async_restore_electricity(self):
        _LOGGER.debug("in async_restore_electricity")
        for dp_id in ELECTRIC_ENTITY[:-3]:
            entity = self.get_entity(f"sunlogin_{self.sn}_{dp_id}")
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})
                    
        _LOGGER.debug("out async_restore_electricity")

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)
        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        # try:
        #     await coordinator.async_config_entry_first_refresh()
        # except: pass
        await self.async_update()
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""

class P1Pro(SunloginPlug):
    """Device for P1 P1Pro"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P1UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITH_ELECTRIC.copy()
        entities = entities[:-4]
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return get_plug_memos(self.config)
    
    async def async_restore_electricity(self):
        _LOGGER.debug("in async_restore_electricity")
        for dp_id in ELECTRIC_ENTITY[:-3]:
            entity = self.get_entity(f"sunlogin_{self.sn}_{dp_id}")
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})
                    
        _LOGGER.debug("out async_restore_electricity")

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        # address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)

        # _LOGGER.debug("new_data %s",self.new_data)        
        # _LOGGER.debug(self.local_address)
        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        # try:
        #     await coordinator.async_config_entry_first_refresh()
        # except: pass

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
        
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        
class P4(SunloginPlug):
    """Device for P4"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P1UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITH_ELECTRIC.copy()
        entities = entities[:-5]
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return get_plug_memos(self.config)
    
    async def async_restore_electricity(self):
        _LOGGER.debug("in async_restore_electricity")
        for dp_id in ELECTRIC_ENTITY[:-3]:
            entity = self.get_entity(f"sunlogin_{self.sn}_{dp_id}")
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})
                    
        _LOGGER.debug("out async_restore_electricity")

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        # address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)

        # update_manager = P1UpdateManager(self)
        coordinator = self.update_manager.coordinator
        # self.hass.async_create_task(coordinator.async_config_entry_first_refresh())
        # try:
        #     await coordinator.async_config_entry_first_refresh()
        # except: pass
        
        _LOGGER.debug("out device async_setup!!!!")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        

class P8(SunloginPlug):
    """Device for P4"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = list()
        self._status = dict()
        self.new_data = dict()
        self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.api = PlugAPI(self.hass, self.default_address)
        self.update_manager = P8UpdateManager(self)
    
    @property
    def entities(self):
        entities = SLOT_X_WITH_ELECTRIC.copy() + EXTRA_ENTITY_P8
        # entities = entities + EXTRA_ENTITY_P8
        platform_entities = {}
        if self.remote_address is not None:
            entities.append(DP_REMOTE)
        
        for dp_id in entities:
            platform = PLATFORM_OF_ENTITY[dp_id]
            if platform_entities.get(platform) is None:
                platform_entities[platform] = [dp_id]
            else:
                platform_entities[platform].append(dp_id)
            
        return platform_entities

    @property
    def memos(self):
        return get_plug_memos(self.config)
    
    async def async_restore_electricity(self):
        _LOGGER.debug("in async_restore_electricity")
        for dp_id in ELECTRIC_ENTITY[:-3] + EXTRA_ENTITY_P8[16:]:
            entity = self.get_entity(f"sunlogin_{self.sn}_{dp_id}")
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})
                    
        _LOGGER.debug("out async_restore_electricity")

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        # config = self.config
        _LOGGER.debug("in device async_setup")
        # address = self.remote_address if self.remote_address else self.local_address
        # api = PlugAPI(self.hass, address)
        # api.timeout = config.data[CONF_TIMEOUT]
        # self.api = api
        self.api.inject_dns = True

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.update_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.update_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.update_flag.append(UPDATE_FLAG_VERSION)
        
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
    TICK_N = 6
    UPDATE_INTERVAL = timedelta(seconds=60)
    FIRST_UPDATE_INTERVAL = timedelta(seconds=10)
    CURRENT_UPDATE_INTERVAL = FIRST_UPDATE_INTERVAL
    

    def __init__(self, device):
        """Initialize the update manager."""
        self.device = device
        self.device.api.timeout = (8,8)
        # self.SCAN_INTERVAL = timedelta(seconds=scan_interval)
        self.coordinator = DataUpdateCoordinator(
            device.hass,
            _LOGGER,
            name=f"{device.name} ({device.model} at {device.sn})",
            update_method=self.async_update,
            update_interval=self.CURRENT_UPDATE_INTERVAL,
        )
        self.available = None
        self.last_update = dt_util.utcnow()

    def change_update_interval(self):
        if self.coordinator.update_interval == self.FIRST_UPDATE_INTERVAL:
            self.CURRENT_UPDATE_INTERVAL = self.UPDATE_INTERVAL
            self.coordinator.update_interval = self.UPDATE_INTERVAL
            self.coordinator.async_set_updated_data(data=self.device._status)
            _LOGGER.debug(f"{self.device.name} change update interval")

    async def async_update(self):
        """Fetch data from the device and update availability."""
        try:
            # data = None
            # if self.TICK_N == 1 or math.ceil(self.UPDATE_COUNT % self.TICK_N) == 1:
            #     data = await self.async_fetch_data()
            data = await self.async_fetch_data()
            self.change_update_interval()
        except Exception as err:
            if (self.available or self.available is None) and (
                dt_util.utcnow() - self.last_update > self.CURRENT_UPDATE_INTERVAL * 3
            ):
                self.available = False
                self.change_update_interval()
                _LOGGER.warning(
                    "Disconnected from %s (%s at %s)",
                    self.device.name,
                    self.device.model,
                    self.device.api.address,
                )
            #force update
            self.coordinator.async_update_listeners()
            self.device.api.timeout = None
            raise UpdateFailed(err) from err
        
        if self.available is False:
            _LOGGER.warning(
                "Connected to %s (%s at %s)",
                self.device.name,
                self.device.model,
                self.device.api.address,
            )
        self.available = True
        self.last_update = dt_util.utcnow()
        self.UPDATE_COUNT += 1
        self.device.api.timeout = None
        return data

    @abstractmethod
    async def async_fetch_data(self):
        """Fetch data from the device."""


class P2UpdateManager(SunloginUpdateManager):
    "Plug without electric"

    error_flag = 0

    async def async_process_update_flag(self):
        if UPDATE_FLAG_SN in self.device.update_flag:
            await self.device.async_update_sn()

        if UPDATE_FLAG_IP in self.device.update_flag:
            await self.device.async_update_ip()

        if UPDATE_FLAG_VERSION in self.device.update_flag:
            await self.device.async_update_fw_version()

    async def async_fetch_data(self):
        """Fetch data from the device."""
        await self.async_process_update_flag()

        sn = self.device.sn
        api = self.device.api
        status = self.device._status

        try:
            resp = await api.async_get_status(sn)
            _LOGGER.debug(f"{self.device.name} (GET_STATUS): {resp.text}")
            r_json = resp.json()
            status.update(plug_status_process(r_json))
        except: 
            self.error_flag += 1
        
        _LOGGER.debug(f"{self.device.name}: {self.device._status}")

        self.UPDATE_COUNT += 1
        if self.error_flag > 0:
            self.error_flag = 0
            raise requests.exceptions.ConnectionError
        return status

class P1UpdateManager(SunloginUpdateManager):
    "Plug with electric"

    last_power_consumes_update = datetime.fromtimestamp(0, timezone.utc)
    error_flag = 0

    async def async_process_update_flag(self):
        if UPDATE_FLAG_SN in self.device.update_flag:
            await self.device.async_update_sn()

        if UPDATE_FLAG_IP in self.device.update_flag:
            await self.device.async_update_ip()

        if UPDATE_FLAG_VERSION in self.device.update_flag:
            await self.device.async_update_fw_version()

    async def async_fetch_data(self):
        """Fetch data from the device."""
        await self.async_process_update_flag()

        sn = self.device.sn
        api = self.device.api
        status = self.device._status
        # if value := self.coordinator.data is not None:
        #     status.update(value)
        try:
            resp = await api.async_get_electric(sn)
            _LOGGER.debug(f"{self.device.name} (GET_ELECTRIC): {resp.text}")
            r_json = resp.json()
            status.update(plug_electric_process(r_json))
        except: 
            self.error_flag += 1

        try:
            resp = await api.async_get_status(sn)
            _LOGGER.debug(f"{self.device.name} (GET_STATUS): {resp.text}")
            r_json = resp.json()
            status.update(plug_status_process(r_json))
        except: 
            self.error_flag += 1

        # if self.device.remote_address and dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
        if dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
            try:
                resp = await api.async_get_power_consumes(sn)
                # _LOGGER.debug(resp.text)
                r_json = resp.json()
                status.update(plug_power_consumes_process(r_json))
                self.last_power_consumes_update = dt_util.utcnow()
            except: 
                self.error_flag += 1
        
        _LOGGER.debug(f"{self.device.name}: {self.device._status}")

        self.UPDATE_COUNT += 1
        if self.error_flag > 0:
            self.error_flag = 0
            raise requests.exceptions.ConnectionError
        return status


class P8UpdateManager(SunloginUpdateManager):
    "For P8 series"

    last_power_consumes_update = datetime.fromtimestamp(0, timezone.utc)
    error_flag = 0

    async def async_process_update_flag(self):
        if UPDATE_FLAG_SN in self.device.update_flag:
            await self.device.async_update_sn()

        if UPDATE_FLAG_IP in self.device.update_flag:
            await self.device.async_update_ip()

        if UPDATE_FLAG_VERSION in self.device.update_flag:
            await self.device.async_update_fw_version()

    async def async_fetch_data(self):
        """Fetch data from the device."""
        await self.async_process_update_flag()

        sn = self.device.sn
        api = self.device.api
        status = self.device._status
        # if value := self.coordinator.data is not None:
        #     status.update(value)
        try:
            resp = await api.async_get_electric(sn)
            _LOGGER.debug(f"{self.device.name} (GET_ELECTRIC): {resp.text}")
            r_json = resp.json()
            status.update(plug_electric_process(r_json))
        except: 
            self.error_flag += 1

        try:
            resp = await api.async_get_status(sn)
            _LOGGER.debug(f"{self.device.name} (GET_STATUS): {resp.text}")
            r_json = resp.json()
            status.update(plug_status_process(r_json))
        except: 
            self.error_flag += 1

        # if self.device.remote_address and dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
        if dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
            for index in range(8+1):
                try:
                    resp = await api.async_get_power_consumes(sn, index=index)
                    r_json = resp.json()
                    status.update(plug_power_consumes_process(r_json, index=index))
                    self.last_power_consumes_update = dt_util.utcnow()
                except: 
                    self.error_flag += 1
        
        _LOGGER.debug(f"{self.device.name}: {self.device._status}")

        self.UPDATE_COUNT += 1
        if self.error_flag > 0:
            self.error_flag = 0
            raise requests.exceptions.ConnectionError
        return status


# class FakeP8UpdateManager(SunloginUpdateManager):
#     "Fake"

#     last_power_consumes_update = datetime.fromtimestamp(0, timezone.utc)
#     error_flag = 0

#     async def async_process_update_flag(self):
#         if UPDATE_FLAG_SN in self.device.update_flag:
#             await self.device.async_update_sn()

#         if UPDATE_FLAG_IP in self.device.update_flag:
#             await self.device.async_update_ip()

#         if UPDATE_FLAG_VERSION in self.device.update_flag:
#             await self.device.async_update_fw_version()

#     async def async_fetch_data(self):
#         """Fetch data from the device."""
#         await self.async_process_update_flag()

#         sn = self.device.sn
#         api = self.device.api
#         status = self.device._status
#         # if value := self.coordinator.data is not None:
#         #     status.update(value)
#         try:
#             resp = await api.async_get_electric(sn)
#             _LOGGER.debug(f"{self.device.name} (GET_ELECTRIC): {resp.text}")
#             r_json = GET_PLUG_ELECTRIC_FAKE_DATA_P8.copy()
#             status.update(plug_electric_process(r_json))
#         except: 
#             self.error_flag += 1

#         try:
#             resp = await api.async_get_status(sn)
#             _LOGGER.debug(f"{self.device.name} (GET_STATUS): {resp.text}")
#             r_json = GET_PLUG_STATUS_FAKE_DATA_P8.copy()
#             status.update(plug_status_process(r_json))
#         except: 
#             self.error_flag += 1

#         # if self.device.remote_address and dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
#         if dt_util.utcnow() - self.last_power_consumes_update > timedelta(minutes=15):
#             _LOGGER.debug('in async_get_power_consumes')
#             for index in range(8+1):
#                 _LOGGER.debug(index)
#                 try:
#                     resp = await api.async_get_power_consumes('',index=index)
#                     _LOGGER.debug(resp.ok)
#                     _LOGGER.debug(resp.text)
#                     r_json = resp.json()
#                     status.update(plug_power_consumes_process(r_json, index=index))
#                     _LOGGER.debug('out async_get_power_consumes')
#                     self.last_power_consumes_update = dt_util.utcnow()
#                 except: 
#                     self.error_flag += 1
        
#         _LOGGER.debug(f"{self.device.name}: {self.device._status}")

#         self.UPDATE_COUNT += 1
#         if self.error_flag > 0:
#             self.error_flag = 0
#             raise requests.exceptions.ConnectionError
#         return status


class PlugConfigUpdateManager():

    TICK_N = 2
    UPDATE_INTERVAL = timedelta(hours=2)
    FIRST_UPDATE_INTERVAL = timedelta(minutes=2)
    CURRENT_UPDATE_INTERVAL = FIRST_UPDATE_INTERVAL

    def __init__(self, hass):
        """Initialize the update manager."""
        self.hass = hass
        self.devices = list()
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Config Update (Plug at 0x0001)",
            update_method=self.async_update,
            update_interval=self.CURRENT_UPDATE_INTERVAL,
        )
        self.last_update = dt_util.utcnow()
        self.coordinator.async_add_listener(self.nop)

    # def add_listener(self):
    #     self.coordinator.async_add_listener(self.nop)

    def nop(self):
        ''''''

    def change_update_interval(self):
        if self.coordinator.update_interval == self.FIRST_UPDATE_INTERVAL:
            self.CURRENT_UPDATE_INTERVAL = self.UPDATE_INTERVAL
            self.coordinator.update_interval = self.UPDATE_INTERVAL
            self.coordinator.async_set_updated_data(data=self.device._status)
            _LOGGER.debug(f"PlugConfigUpdateManager change update interval")

    async def async_update(self):
        """Fetch data from the device and update availability."""
        try:
            for device in self.devices:
                device.update_configuration()
                _LOGGER.debug(f"{device.name} ({device.sn})")
            self.change_update_interval()
        except: 
            self.change_update_interval()
            return False
            
        self.last_update = dt_util.utcnow()
        return True
        

class DNSUpdateManger():

    refresh_ttl = timedelta(hours=12)
    server = 'ip33'

    def __init__(self, hass):
        self.hass = hass
        self.dns = DNS(hass, self.server)
        self.devices = list()
        self.coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=f"DNS Update (query at {self.server})",
            update_method=self.dns.async_update,
            update_interval=self.refresh_ttl,
        )
        self.coordinator.async_add_listener(self.nop)

    def nop(self):
        for device in self.devices:
            if device.api._inject_dns:
                device.api._inject_dns = True


class Token():
    access_token = None
    refresh_token = None
    create_time = None
    coordinator = None
    _api_v1 = None
    _api_v2 = None
    interval = 600
    is_new_client = False
    
    def __init__(self, hass):
        self.hass = hass
        self.refresh_expire = 0
        self.refresh_ttl = timedelta(seconds=150)
        self.quick_refresh_ttl = timedelta(seconds=10)

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
        if self.access_token == 'a' or self.access_token is None or self.refresh_token == 'r' or self.refresh_token is None or time.time() > self.refresh_expire:
            return False
        return True

    def need_update(self):
        info = toekn_decode(self.access_token)
        exp = info.get('exp', 0)
        if time.time() >= exp:
            return True
        return False
    
    def change_update_interval(self, interval):
        if self.coordinator.update_interval != interval:
            self.coordinator.update_interval = interval
            self.coordinator.async_set_updated_data(data=None)
            _LOGGER.debug(f"TokenUpdateManager change update interval")

    async def login_new_client(self):
        error, resp = await async_request_error_process(self._api_v1.async_get_auth_code)
        if error is not None:
            _LOGGER.debug(error)
            return
        r_json = resp.json()
        code = r_json.get('code')

        error, resp = await async_request_error_process(self._api_v1.async_grant_auth_code, self.access_token, code)
        if error is not None:
            _LOGGER.debug(error)
            return
        
        error, resp = await async_request_error_process(self._api_v1.async_login_terminals_by_code, self.access_token, code)
        if error is not None:
            _LOGGER.debug(error)
            return
        
        self.is_new_client = False
        _LOGGER.debug('login_new_client success!')
        return True

    async def async_update(self):
        if not self.check():
            return
        
        if self.is_new_client:
            if self.need_update():
                _LOGGER.debug('need reauth')
                return
            result = await self.login_new_client()
            if not result: return

        if not self.need_update() and time.time() - self.create_time < self.interval - 10:
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
            if error == 'lt/new_device_alert':
                self.is_new_client = True
            self.change_update_interval(self.quick_refresh_ttl)
            return None
        
        self.change_update_interval(self.refresh_ttl)
        r_json = resp.json()
        return r_json

    async def async_update_by_session(self):
        ''''''


class PlugAPI():
    VERSION = 2
    _inject_dns = None

    def __init__(self, hass, address):
        self.hass = hass
        self._address = address
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

    @property
    def inject_dns(self):
        return self._inject_dns
    
    @inject_dns.setter
    def inject_dns(self, inject_dns):
        self._inject_dns = inject_dns
        self.address = self.process_address(self._address)
        self._api.VERIFY = False

    def process_address(self, address):
        if self.VERSION == 2 and address[-4:] == '8000':
            dns_update = self.hass.data[DOMAIN][CONF_DNS_UPDATE]
            if self.inject_dns and (ip_address := dns_update.dns.cache.get(PLUG_DOMAIN)) is not None:
                address = PLUG_URL.replace(PLUG_DOMAIN, ip_address)
            else:
                address = PLUG_URL
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

    async def async_get_power_consumes(self, sn, index=0):
        return await self._api.async_get_power_consumes(sn, index=index)
    
