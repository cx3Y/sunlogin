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
import pyqrcode
import io
import async_timeout
import aiohttp
from .sunlogin_api import CloudAPI, CloudAPI_V2, PlugAPI_V1, PlugAPI_V2_FAST
# from .fake_data import GET_PLUG_ELECTRIC_FAKE_DATA_P8, GET_PLUG_STATUS_FAKE_DATA_P8
from .dns_api import DNS
from .updater import *
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
from homeassistant.components import persistent_notification
from homeassistant import config_entries
from .dns_api import change_dns_server
from .updater import (
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL,
    DEFAULT_DNS_UPDATE_INTERVAL,
    DEFAULT_CONFIG_UPDATE_INTERVAL,
    DEFAULT_TOKEN_UPDATE_INTERVAL,
    DEFAULT_DEVICES_UPDATE_INTERVAL,
    MIN_REMOTE_INTERVAL,
    MIN_LOCAL_INTERVAL,
)
from .const import (
    DOMAIN,
    PLUG_DOMAIN,
    PLUG_URL,
    SL_DEVICES,
    BLANK_SN,
    CONFIG,
    CONF_TOKEN,
    CONF_SMARTPLUG,
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
    CONF_UPDATE_MANAGER,
    CONF_STORE_MANAGER,
    CONF_REMOTE_UPDATE_INTERVAL,
    CONF_LOCAL_UPDATE_INTERVAL,
    CONF_POWER_CONSUMES_UPDATE_INTERVAL,
    CONF_CONFIG_UPDATE_INTERVAL,
    CONF_TOKEN_UPDATE_INTERVAL,
    CONF_ENABLE_DEVICES_UPDATE,
    CONF_DEVICES_UPDATE_INTERVAL,
    CONF_ENABLE_DNS_INJECTOR,
    CONF_DNS_SERVER,
    CONF_DNS_UPDATE_INTERVAL,
    CONF_ENABLE_PROXY,
    CONF_PROXY_SERVER,
    CONF_ENABLE_ENCRYPT_LOG,
    DEFAULT_ENABLE_DNS_INJECTOR,
    DEFAULT_DNS_SERVER,
    DEFAULT_ENABLE_PROXY,
    DEFAULT_PROXY_SERVER,
    CONF_DNS_UPDATE,
    CONF_RELOAD_FLAG,
    HTTP_SUFFIX, 
    LOCAL_PORT,
)


_LOGGER = logging.getLogger(__name__)

PLUG_API_VERSION = 2

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

async def async_login_new_client(hass, access_token):
    api = CloudAPI(hass)
    error, resp = await async_request_error_process(api.async_get_auth_code)
    if error is not None:
        _LOGGER.error("login_new_client failed, error: %s", error)
        return
    r_json = resp.json()
    code = r_json.get('code')

    error, resp = await async_request_error_process(api.async_grant_auth_code, access_token, code)
    if error is not None:
        _LOGGER.error("login_new_client failed, error: %s", error)
        return
    
    error, resp = await async_request_error_process(api.async_login_terminals_by_code, access_token, code)
    if error is not None:
        _LOGGER.error("login_new_client failed, error: %s", error)
        return
    
    return True

async def aysnc_dns_update(hass):
    dns = DNS(hass, 'ip33')
    if dns.cache.get(PLUG_DOMAIN) is None:
        dns.set_domain(PLUG_DOMAIN)
    await dns.async_update()
    ip = dns.get_ip(PLUG_DOMAIN)
    if ip is not None:
        api = PlugAPI_V2_FAST(hass, PLUG_URL)
        api._process_address[PLUG_URL] = PLUG_URL.replace(PLUG_DOMAIN, ip)
        # api.process_cert()
        _LOGGER.debug(f"DNS update success, {PLUG_DOMAIN}: {ip}")

async def async_devices_update(hass):
    token = get_token(hass)
    api = CloudAPI(hass)
    error, resp = await async_request_error_process(api.async_get_devices_list, token.access_token)

    if error is not None:
        return error
    
    r_json = resp.json()
    if len(r_json.get('devices', '')) != 0:
        device_list = device_filter(r_json["devices"])
        store_manager = get_store_manager(hass)
        store_manager.update_device(device_list)
    _LOGGER.debug("Devices update success")

async def async_guess_model(hass, ip):
    model = None
    sn = None
    local_address = HTTP_SUFFIX + ip + LOCAL_PORT
    plug_api = PlugAPI_V1(hass, local_address)

    resp_sn = await plug_api.async_get_sn()
    sn_json = resp_sn.json()
    sn = sn_json[CONF_DEVICE_SN]
    device_type = sn_json.get('type')

    if device_type == 'e':
        model = 'C1-2'
    elif device_type == 'plug-b2':
        model = 'C1Pro'
    elif device_type == 'o':
        model = 'C1'
    elif device_type == 'plug-c2':
        model = 'C2'
    elif device_type == 'P1Pro':
        model = 'P1Pro'
    elif device_type == 'e2':
        model = 'P1'
    elif device_type == 'ps-3310':
        model = 'P2'
    elif device_type == 'P4':
        model = 'P4'
    elif device_type == 'P8':
        model = 'P8'
    else:
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

def get_entities(tag):
    electricity_entity = [
        DP_ELECTRICITY_HOUR, 
        DP_ELECTRICITY_DAY, 
        DP_ELECTRICITY_WEEK, 
        DP_ELECTRICITY_MONTH, 
        DP_ELECTRICITY_LASTMONTH,
    ]
    electric_entity = [
        DP_POWER, 
        DP_CURRENT, 
        DP_VOLTAGE,
    ]
    slot_x_without_electric = [
        DP_LED, 
        DP_DEFAULT, 
        DP_RELAY_0, 
        DP_RELAY_1, 
        DP_RELAY_2, 
        DP_RELAY_3, 
        DP_RELAY_4, 
        DP_RELAY_5, 
        DP_RELAY_6, 
        DP_RELAY_7,
    ]
    extra_p8 = [
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

    slot_x_with_electric = electricity_entity + electric_entity + slot_x_without_electric
    if tag == 'electricity':
        return electricity_entity
    elif tag == 'electric':
        return electric_entity
    elif tag == 'slot_x_without_electric':
        return slot_x_without_electric
    elif tag == 'slot_x_with_electric':
        return slot_x_with_electric
    elif tag == 'p8_extra_electricity':
        return extra_p8[16:]
    elif tag == 'electricity_hour':
        return [DP_ELECTRICITY_HOUR, *extra_p8[16:24]]
    elif tag == 'electricity_day':
        return [DP_ELECTRICITY_DAY, *extra_p8[24:32]]
    elif tag == 'electricity_week':
        return [DP_ELECTRICITY_WEEK, *extra_p8[32:40]]
    elif tag == 'electricity_month':
        return [DP_ELECTRICITY_MONTH, *extra_p8[40:48]]
    elif tag == 'electricity_lastmonth':
        return [DP_ELECTRICITY_LASTMONTH, *extra_p8[48:56]]

    elif 'C2' in tag or 'C1-2' == tag:
        return slot_x_with_electric[:-7]
    elif 'C1' in tag:
        return slot_x_without_electric[:-7]
    elif 'P1' in tag:
        return slot_x_with_electric[:-4]
    elif 'P2' in tag:
        return slot_x_without_electric[:-5]
    elif 'P4' in tag:
        return slot_x_with_electric[:-5]
    elif 'P8' in tag:
        return slot_x_with_electric + extra_p8

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

    if (sub_electric := data.get('sub')) is not None and isinstance(sub_electric, list):
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
    dp_electricity_hour = get_entities('electricity_hour')[index]
    dp_electricity_day = get_entities('electricity_day')[index]
    dp_electricity_week = get_entities('electricity_week')[index]
    dp_electricity_month = get_entities('electricity_month')[index]
    dp_electricity_lastmonth = get_entities('electricity_lastmonth')[index]
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

def get_token(hass):
    entry_id = config_entries.current_entry.get().entry_id
    token = hass.data[DOMAIN][CONFIG][entry_id][CONF_TOKEN]
    return token

def get_store_manager(hass) -> StoreManager:
    entry = config_entries.current_entry.get()
    store_manager = hass.data[DOMAIN][CONFIG][entry.entry_id][CONF_STORE_MANAGER]
    return store_manager

def get_update_manager(hass) -> UpdateManager:
    entry = config_entries.current_entry.get()
    config = hass.data[DOMAIN][CONFIG][entry.entry_id]
    update_manager = config[CONF_UPDATE_MANAGER]
    return update_manager

def make_qrcode_base64_v2(r_json):
    qrdata = r_json.get('qrdata')
    key = r_json.get('key')
    if qrdata is None:
        return 
    buffer = io.BytesIO()
    url = pyqrcode.create(qrdata)
    # url.png(buffer, scale=5, module_color="#EEE", background="#FFF")
    url.png(buffer, scale=5, module_color="#000", background="#FFF")
    image_base64 = str(base64.b64encode(buffer.getvalue()), encoding='utf-8')
    image = f'![image](data:image/png;base64,{image_base64})'
    _LOGGER.debug("make_qrcode_img: %s", qrdata)

    return {"image": image, "time": time.time(), "key": key}
    
def device_filter(device_list):
    devices = dict()
    if isinstance(device_list, list):
        device_list = {dev["sn"]: dev for dev in device_list}
    for sn, dev in device_list.items():
        device_type = dev.get('device_type', 'unknow')
        if device_type == CONF_SMARTPLUG and dev.get('isenable', True):
            devices[sn] = dev

    return devices    

def config_options(hass, entry, diff):
    data = dict()
    update_manager = hass.data[DOMAIN][CONFIG][entry.entry_id][CONF_UPDATE_MANAGER]

    if (remote := diff.get(CONF_REMOTE_UPDATE_INTERVAL)) is not None and remote >= MIN_REMOTE_INTERVAL:
        DEFAULT_UPDATE_INTERVAL.remote = remote
        data[CONF_REMOTE_UPDATE_INTERVAL] = remote
    if (local := diff.get(CONF_LOCAL_UPDATE_INTERVAL)) is not None and local >= MIN_LOCAL_INTERVAL:
        DEFAULT_UPDATE_INTERVAL.local = local
        data[CONF_LOCAL_UPDATE_INTERVAL] = local
    # if (power_consumes_interval := diff.get(CONF_POWER_CONSUMES_UPDATE_INTERVAL)) is not None and power_consumes_interval >= 1200:
    #     DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL.interval = power_consumes_interval
    if (config_interval := diff.get(CONF_CONFIG_UPDATE_INTERVAL)) is not None and config_interval >= 900:
        DEFAULT_CONFIG_UPDATE_INTERVAL.interval = config_interval
        data[CONF_CONFIG_UPDATE_INTERVAL] = config_interval
    if (token_interval := diff.get(CONF_TOKEN_UPDATE_INTERVAL)) is not None and token_interval >= 600:
        DEFAULT_TOKEN_UPDATE_INTERVAL.interval = token_interval
        data[CONF_TOKEN_UPDATE_INTERVAL] = token_interval

    if diff.get(CONF_ENABLE_DEVICES_UPDATE) is None:
        pass
    elif (devices_update := diff.get(CONF_ENABLE_DEVICES_UPDATE)):
        _async_devices_update = functools.partial(async_devices_update, hass)
        update_manager.add_task('devices_update', _async_devices_update, DEFAULT_DEVICES_UPDATE_INTERVAL, 60)
        data[CONF_ENABLE_DEVICES_UPDATE] = devices_update
    else:
        update_manager.del_task('devices_update')
        data[CONF_ENABLE_DEVICES_UPDATE] = False
    if (devices_interval := diff.get(CONF_DEVICES_UPDATE_INTERVAL)) is not None and devices_interval >= 120:
        DEFAULT_DEVICES_UPDATE_INTERVAL.interval = devices_interval
        data[CONF_DEVICES_UPDATE_INTERVAL] = devices_interval

    if diff.get(CONF_ENABLE_DNS_INJECTOR) is None:
        pass
    elif (dns_enable := diff.get(CONF_ENABLE_DNS_INJECTOR)):
        _aysnc_dns_update = functools.partial(aysnc_dns_update, hass)
        update_manager.add_task('dns_update', _aysnc_dns_update, DEFAULT_DNS_UPDATE_INTERVAL)
        data[CONF_ENABLE_DNS_INJECTOR] = dns_enable
    else:
        update_manager.del_task('dns_update')
        api = PlugAPI_V2_FAST(hass, PLUG_URL)
        api._process_address[PLUG_URL] = PLUG_URL
        # for key, _ in api._process_address.items():
        #     api._process_address[key] = key
        data[CONF_ENABLE_DNS_INJECTOR] = False
    if (dns_server := diff.get(CONF_DNS_SERVER)) is not None:
        change_dns_server(dns_server)
        data[CONF_DNS_SERVER] = dns_server
    if (dns_interval := diff.get(CONF_DNS_UPDATE_INTERVAL)) is not None and dns_interval >= 60:
        DEFAULT_DNS_UPDATE_INTERVAL.interval = dns_interval
        data[CONF_DNS_UPDATE_INTERVAL] = dns_interval
        
    if diff.get(CONF_ENABLE_PROXY) is None:
        pass
    elif (proxy_enable := diff.get(CONF_ENABLE_PROXY)):
        if (proxy_server := diff.get(CONF_PROXY_SERVER)) is not None:
            CloudAPI_V2(hass).proxies = proxy_server
        else:
            CloudAPI_V2(hass).proxies = entry.options.get(CONF_PROXY_SERVER)
        data[CONF_ENABLE_PROXY] = proxy_enable
    else:
        CloudAPI_V2(hass).proxies = None
        data[CONF_ENABLE_PROXY] = False
    if (proxy_server := diff.get(CONF_PROXY_SERVER)) is not None:
        data[CONF_PROXY_SERVER] = proxy_server

    if (encrypt_enable := diff.get(CONF_ENABLE_ENCRYPT_LOG)) is not None:
        data[CONF_ENABLE_ENCRYPT_LOG] = encrypt_enable
    
    return data
    

class SunLogin:
    def __init__(self, hass):
        """Initialize the class."""
        self.hass = hass
        self.userid = None
        self.token = Token()
        self._api_v1 = CloudAPI(hass)
        self._api_v2 = CloudAPI_V2(hass)
        self.device_list = dict()

    async def async_get_access_token_by_password(self, username, password):
        error, resp = await async_request_error_process(self._api_v1.async_login_by_password, username, password)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.token.config = r_json
        self.userid = self.token.token_decode().get('uid')

        return "ok"

    async def async_get_access_token_by_sms(self, username, smscode):

        error, resp = await async_request_error_process(self._api_v1.async_login_by_sms, username, smscode)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.token.config = r_json
        self.userid = self.token.token_decode().get('uid')

        return "ok"
    
    async def async_get_access_token_by_qrcode(self, secret):
        error, resp = await async_request_error_process(self._api_v2.async_login_by_qrcode, secret)

        if error is not None:
            return error
        
        r_json = resp.json()
        self.token.config = r_json
        self.userid = r_json.get('userid')

        return "ok"    

    async def async_get_devices_list(self):
        error, resp = await async_request_error_process(self._api_v1.async_get_devices_list, self.token.access_token)

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
    _available = None
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
        if self._available is None:
            return False
        return self._available

    @property
    def fw_version(self):
        if self._fw_version != "0.0.0":
            return self._fw_version
        elif (version := self.config.get(CONF_DEVICE_VERSION)) is not None:
            return version
        return self._fw_version
    
    @fw_version.setter
    def fw_version(self, fw_version):
        if fw_version is not None:
            self._fw_version = fw_version

    @staticmethod
    async def async_update(hass) -> None:
        """Update the device and related entities.

        Triggered when the device is renamed on the frontend.
        """
        device_registry = dr.async_get(hass)
        entry = config_entries.current_entry.get()
        assert entry.unique_id
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.unique_id)}
        )
        assert device_entry
        device_registry.async_update_device(device_entry.id, name=entry.title)
        #await hass.config_entries.async_reload(entry.entry_id)

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
    update_manager = None
    config_flag = None
    update_interval = None
    device_entry = None
    token = None
    
    @property
    def remote_address(self):
        remote_address = self.config.get(CONF_DEVICE_ADDRESS)
        if remote_address is None:
            return None
        if PLUG_API_VERSION == 1:
            return remote_address
        elif PLUG_API_VERSION == 2:
            return PLUG_URL
    
    @property
    def local_address(self):
        if self._ip is not None: 
            return HTTP_SUFFIX + self._ip + LOCAL_PORT
        elif (ip := self.config.get(CONF_DEVICE_IP_ADDRESS)) is not None:
            return HTTP_SUFFIX + ip + LOCAL_PORT
    
    @property
    def default_address(self):
        if self.remote_address is not None:
            return self.remote_address
        elif self.local_address is not None:
            return self.local_address
        else: # xxx-V3 only (*)  no remote_address, but it is not local
            return PLUG_URL
    
    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the device."""
        return "sunlogin_plug_{}".format(self.config.get(CONF_DEVICE_SN))
    
    @property
    def is_local(self):
        if self.remote_address is None and self.local_address is not None:
            return True
        else:
            return False

    def status(self, dp_id):
        return self._status.get(dp_id)
    
    def available(self, dp_id):
        if dp_id == DP_REMOTE:
            if self.status(dp_id) is not None and self.local_address is not None and self.remote_address is not None:
                return True
            else: 
                return False
        return self._available
    
    def set_dp_remote(self, status):
        if status is None:
            return
        elif status and self.remote_address is not None:
            # self.api = PlugAPI(self.hass, self.remote_address)
            self.api.address = self.remote_address
            self._status.update({DP_REMOTE: status})
            self.update_interval.interval = status
        elif not status and self.local_address is not None:
            # self.api = PlugAPI(self.hass, self.local_address)
            self.api.address = self.local_address
            self._status.update({DP_REMOTE: status})
            self.update_interval.interval = status
        
        # entity = self.get_entity(f"sunlogin_{self.sn}_{DP_REMOTE}")
        # _LOGGER.debug(entity)
        # entity.async_write_ha_state()

    def get_sersor_remark(self, dp_id):
        return None
            
    def get_sn_by_configuration(self):
        return self.config.get(CONF_DEVICE_SN)
    
    def pop_update_flag(self, flag):
        for index, _flag in enumerate(self.config_flag):
            if _flag == flag:
                self.config_flag.pop(index)
                break
    
    def write_ha_state(self):
        for dp_id, entity in self._entities.items():
            entity._recv_data()
            # entity.async_write_ha_state()
        
    async def async_restore_dp_remote(self):
        entity = self._entities.get(DP_REMOTE)
        last_state = await entity.async_get_last_state()
        if last_state is None:
            self.set_dp_remote(1)
        elif last_state.state == 'off':
            self.set_dp_remote(0)
        elif last_state.state == 'on':
            self.set_dp_remote(1)
        else:
            self.set_dp_remote(1)

    async def async_restore_electricity(self):
        entities = get_entities('electricity')
        for dp_id in entities:
            entity = self._entities.get(dp_id)
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})

    async def async_get_firmware_version(self) -> str | None:
        """Get firmware version."""
        resp = await self.api.async_get_info(self.sn, self.token.access_token)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_VERSION]

    async def async_get_ip_address(self) -> str | None:
        """Get device ip address."""
        resp = await self.api.async_get_wifi_info(self.sn, self.token.access_token)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_IP_ADDRESS]
    
    async def async_get_sn_by_api(self) -> str | None:
        """Get device series number."""
        resp = await self.api.async_get_sn(access_token = self.token.access_token)
        
        r_json = resp.json()
        return r_json[CONF_DEVICE_SN]

    async def async_set_dp(self, dp_id, status):
        if dp_id == DP_REMOTE:
            self.set_dp_remote(status)
            return
        elif dp_id == DP_LED:
            resp =  await self.api.async_set_led(self.sn, status, self.token.access_token)
        elif dp_id == DP_DEFAULT:
            resp = await self.api.async_set_default(self.sn, status, self.token.access_token)
        else:
            index = int(dp_id[-1])
            resp = await self.api.async_set_status(self.sn, index, status, self.token.access_token)

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

    async def async_status_update(self):

        if UPDATE_FLAG_SN in self.config_flag:
            await self.async_update_sn()

        if UPDATE_FLAG_IP in self.config_flag:
            await self.async_update_ip()

        if UPDATE_FLAG_VERSION in self.config_flag:
            await self.async_update_fw_version()

        try:
            resp = await self.api.async_get_status(self.sn, self.token.access_token)
            _LOGGER.debug(f"{self.name} (api.async_get_status): {resp.text}")
            r_json = resp.json()
            self._status.update(plug_status_process(r_json))
            self._available = True
        except Exception as e: 
            _LOGGER.debug(f"{self.name} (api.async_get_status): {e}")
            self._available = False

        self.write_ha_state()   

    async def async_electric_update(self):
        try:
            resp = await self.api.async_get_electric(self.sn, self.token.access_token)
            _LOGGER.debug(f"{self.name} (api.async_get_electric): {resp.text}")
            r_json = resp.json()
            self._status.update(plug_electric_process(r_json))
            self._available = True
        except Exception as e: 
            _LOGGER.debug(f"{self.name} (api.async_get_electric): {e}")
            self._available = False

        self.write_ha_state()

    async def async_power_consumes_update(self):
        try:
            resp = await self.api.async_get_power_consumes(self.sn)
            r_json = resp.json()
            self._status.update(plug_power_consumes_process(r_json))
        except: 
            if self.status(DP_REMOTE):
                self._available = False
        
        self.write_ha_state()
    
    async def async_update_sn(self):
        try:
            self.sn = await self.async_get_sn_by_api()
            store_manager = get_store_manager(self.hass)
            store_manager.update_device_config(self.sn, {CONF_DEVICE_SN: self.sn})
            self.pop_update_flag(UPDATE_FLAG_SN)
        except:
            pass

    async def async_update_ip(self):
        try:
            self._ip = await self.async_get_ip_address()
            store_manager = get_store_manager(self.hass)
            store_manager.update_device_config(self.sn, {CONF_DEVICE_IP_ADDRESS: self._ip})
            self.pop_update_flag(UPDATE_FLAG_IP)
        except:
            pass
    
    async def async_update_fw_version(self):
        try:
            self.fw_version = await self.async_get_firmware_version()
            if self.fw_version != self.config.get(CONF_DEVICE_VERSION):
                store_manager = get_store_manager(self.hass)
                store_manager.update_device_config(self.sn, {CONF_DEVICE_VERSION: self.fw_version})

                device_registry = dr.async_get(self.hass)
                device_entry = device_registry.async_get_device(identifiers={(DOMAIN, self.sn)})
                assert device_entry
                device_registry.async_update_device(device_entry.id, sw_version=self.fw_version)
            self.pop_update_flag(UPDATE_FLAG_VERSION)
        except: 
            """"""
            # if (version := self.config.get(CONF_DEVICE_VERSION)) is not None:
            #     self.fw_version = version

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
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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
    
    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)

        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""

class P2(SunloginPlug):
    """Device for P2"""
    
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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

    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)

        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""



class C2(SunloginPlug):
    """Device for C2 C2-BLE"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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
                    
    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)

        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) electric_update", self.async_electric_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) power_consumes_update", self.async_power_consumes_update, DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""

class P1Pro(SunloginPlug):
    """Device for P1 P1Pro"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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

    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)

        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) electric_update", self.async_electric_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) power_consumes_update", self.async_power_consumes_update, DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        
class P4(SunloginPlug):
    """Device for P4"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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

    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        await self.async_restore_electricity()
        
        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)

        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) electric_update", self.async_electric_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) power_consumes_update", self.async_power_consumes_update, DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        

class P8(SunloginPlug):
    """Device for P8 P8Pro"""

    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.sn = config.get(CONF_DEVICE_SN)
        self._entities = dict()
        self._status = dict()
        self.new_data = dict()
        self.config_flag = list()
        # self.update_flag = list()
        # self._ip = config.get(CONF_DEVICE_IP_ADDRESS)
        self.token = get_token(hass)
        self.api = PlugAPI_V2_FAST(self.hass, self.default_address)
        self.update_interval = PlugUpdateInterval(DEFAULT_UPDATE_INTERVAL, int(not self.is_local))
    
    @property
    def entities(self):
        entities = get_entities(self.model)
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
    
    async def async_power_consumes_update(self):
        for index in range(8+1):
            try:
                resp = await self.api.async_get_power_consumes(self.sn, index=index)
                r_json = resp.json()
                self._status.update(plug_power_consumes_process(r_json, index=index))
            except: 
                if self.device.status(DP_REMOTE):
                    self._available = False
        
        self.write_ha_state()
    
    async def async_restore_extra_electricity(self):
        entities = get_entities('p8_extra_electricity')
        for dp_id in entities:
            entity = self._entities.get(dp_id)
            last_state = await entity.async_get_last_state()
            if last_state is not None and isinstance(last_state.state, (int, float)):
                self._status.update({dp_id: last_state.state})

    async def async_setup(self, update_manager) -> bool:
        """Set up the device and related entities."""

        await self.async_restore_electricity()
        await self.async_restore_extra_electricity()
        
        if self.sn == BLANK_SN:
            self.config_flag.append(UPDATE_FLAG_SN)
        
        if self.remote_address:
            self.config_flag.append(UPDATE_FLAG_IP)
            await self.async_restore_dp_remote()

        self.config_flag.append(UPDATE_FLAG_VERSION)
        
        
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) status_update", self.async_status_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) electric_update", self.async_electric_update, self.update_interval)
        update_manager.add_task(f"{self.name}({self.sn[-6:]}) power_consumes_update", self.async_power_consumes_update, DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL)

        _LOGGER.debug(f"{self.name} async_setup success")
        return True
    
    async def async_request(self, *args, **kwargs):
        """Send a request to the device."""
        

class Token():
    _config = None
    _create_time = 0
    _token_expire = 0

    def __init__(self, config=None):
        self.config = config

    @property
    def config(self):
        config = self._config.copy()
        if config.get(CONF_REFRESH_EXPIRE) is None:
            config[CONF_REFRESH_EXPIRE] = self.create_time + 30*24*3600
        return config
    
    @config.setter
    def config(self, config):
        if config is None or not config:
            return
        self._config = config
        self._create_time = config.get(CONF_REFRESH_EXPIRE, time.time()+30*24*3600) - 30*24*3600
        self._token_expire = self.token_decode().get('exp', 0)

    @property
    def access_token(self):
        return self._config.get(CONF_ACCESS_TOKEN)
    
    @property
    def refresh_token(self):
        return self._config.get(CONF_REFRESH_TOKEN)
    
    @property
    def create_time(self):
        return self._create_time

    @property
    def refresh_expire(self):
        return self._config.get(CONF_REFRESH_EXPIRE, self.create_time+30*24*3600) - 60
    
    @property
    def token_expire(self):
        return self._token_expire

    def token_decode(self):
        if not self.validate():
            return dict()
        part1, part2, part3 = self.access_token.split('.')
        part2 += '='*(4-(len(part2)%4))
        info = json.loads(base64.b64decode(part2).decode('utf-8'))
        return info
    
    def validate(self):
        if not self.access_token or self.access_token == 'a':
            return False
        elif not self.refresh_token or self.refresh_token == 'r':
            return False
        
        return True
    
    async def async_refresh_token(self, hass):
        api = CloudAPI(hass)

        if not self.validate() or time.time() > self.refresh_expire:
            _LOGGER.debug('need reauth')
            entry = config_entries.current_entry.get()
            entry.async_start_reauth(hass)
            return
        
        error, resp = await async_request_error_process(api.async_refresh_token, self.access_token, self.refresh_token)
        if error == 'lt/new_device_alert':
            if await async_login_new_client(hass, self.access_token):
                error, resp = await async_request_error_process(api.async_refresh_token, self.access_token, self.refresh_token)
        
        r_json = resp.json()
        self.config = r_json

        store_manager = get_store_manager(hass)
        store_manager.update_token(self.config)
        _LOGGER.debug('Refresh token success')
        




   
