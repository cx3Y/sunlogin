import aiohttp
import asyncio
import requests
import json
import functools
import hashlib
import time
import logging
from abc import ABC
from requests.auth import AuthBase
from requests.adapters import HTTPAdapter
from .const import PLUG_DOMAIN

_LOGGER = logging.getLogger(__name__)

APP_ID = 'kNUC97u86Zr7mt9xeZVl'
# terminal_name shown in the "login devices" list; matches the android UA
TERMINAL_NAME = 'Android Device'
PASSWORD = 'password'
SMS = 'securecode'
SN = 'sn'
# Mirrors the official flutter client (user_agent_utils.dart):
#   SLRC/{version} ({platform},appname=sunloginRemoteClient,handcake)
# Version is kept in sync with the flutter app (pubspec 16.8.0+34767).
# The backend parses this UA (util/ua/useragent.go) and bans exact
# versions (login-terminal disabledLoginVersion); it can be overridden
# at runtime via change_user_agent / the user_agent option.
DEFAULT_USER_AGENT = 'SLRC/16.8.0.34767 (android,appname=sunloginRemoteClient,handcake)'
CLIENT_ID = '8ae73501-7def-5b19-b57d-52d15ae1e40b'
HTTPS_SUFFIX = 'https://'
HTTP_SUFFIX = 'http://'
BASE_URL = HTTPS_SUFFIX + 'api-std.sunlogin.oray.com'
BASE_URL_V2 = HTTPS_SUFFIX + 'user-api-v2.oray.com'
PLUG_URL = HTTPS_SUFFIX + PLUG_DOMAIN
AUTH_CODE = '/authorize/code'
AUTH_REFRESH = '/authorize/refreshing'
AUTH_SESSION = '/authorization/session-token'
QRCODE_APPLY = '/qrcode/apply'
QRCODE_STATUS = '/qrcode/status'
LOGIN_TERMINALS = '/login-terminals'
LOGIN_URL = BASE_URL + '/authorization'
DEVICES_URL = BASE_URL + '/wakeup/devices'
REFRESH_URL_V1 = BASE_URL + AUTH_REFRESH
QRCODE_URL = BASE_URL_V2 + '/qrcode/authorization'
QRCODE_APPLY_URL = BASE_URL_V2 + QRCODE_APPLY
QRCODE_STATUS_URL = BASE_URL_V2 + QRCODE_STATUS
AUTH_CODE_URL = BASE_URL + AUTH_CODE
LOGIN_TERMINALS_URL = BASE_URL + LOGIN_TERMINALS
LOGIN_TERMINALS_SENDCODE_URL = BASE_URL + LOGIN_TERMINALS + '/sendcode'
LOGIN_TERMINALS_CHECKCODE_URL = BASE_URL + LOGIN_TERMINALS + '/checkcode'
REFRESH_URL_V2 = BASE_URL_V2 + AUTH_SESSION
HEAD_AUTH = 'Authorization'
HEAD_CLIENT_ID = 'EX-ClientId'
HEAD_KAL_CLIENT_ID = 'KAL-ClientID'
AUTH_SUFFIX = 'Bearer'
CLIENT_SALT = '==SunLogin@2023=='
LANGUAGE = 'zh-Hans_US'

# Module-level default User-Agent. It can be overridden at runtime
# (see change_user_agent) so that a version banned server-side
# (login-terminal disabledLoginVersion) can be replaced without a code release.
USER_AGENT = DEFAULT_USER_AGENT

VERIFY_METHOD_MOBILE = 'mobile'
VERIFY_METHOD_EMAIL = 'email'


def change_user_agent(user_agent):
    global USER_AGENT
    if user_agent:
        USER_AGENT = user_agent
        _LOGGER.debug("User-Agent changed to %s", user_agent)


def base_headers():
    """Build the standard headers for cloud api requests."""
    return {
        'User-Agent': USER_AGENT,
        'X-AppID': APP_ID,
        'Accept': '*/*',
        'Country-Region': LANGUAGE,
        'Accept-Language': LANGUAGE,
    }

ACTION = "action"
ADDR = "addr"
API = "_api"
PLUG_PATH = "/plug"
KEY = "key"
TIME = "time"
PLUGIN_SCHEMA = "==smart-plug=="
MEMORY_STATUS = "2"
API_ADD_CUT_DOWN = "plug_cntdown_add"
API_BIND = "bind_plug"
API_DELETE_CUT_DOWN = "plug_cntdown_del"
API_DELETE_TIME = "plug_timer_del"
API_ENABLE_TIME = "plug_timer_set"
API_GET_CUT_DOWN = "plug_cntdown_get"
API_GET_PLUG_ELECTRIC = "get_plug_electric"
API_GET_PLUG_INFO = "get_plug_info"
API_GET_POWER_STRIP_TIME = "plug_timer_get"
API_GET_SN = "get_plug_sn"
API_GET_STATUS = "get_plug_status"
API_GET_VERSION = "get_plug_version"
API_GET_WIFI_INFO = "get_plug_wifi"
API_SET_PLUG_DFLTSTAT = "set_plug_dfltstat"
API_SET_PLUG_LED = "set_plug_led"
API_SET_STATUS = "set_plug_status"
API_SET_TIME = "plug_timer_add"
API_UPGRADE = "plug_upgrade"
API_UPGRADE_STATUS = "plug_upgrade_status"


def calc_key_with_time(sn):
    seed = time.strftime('%m%d%H%M')
    raw = sn + PLUGIN_SCHEMA + seed
    
    return {TIME: seed, KEY: hashlib.md5(raw.encode()).hexdigest()}
    
def calc_key_with_str(sn):
    seed = 'scry'
    raw = sn + PLUGIN_SCHEMA + seed
    
    return {TIME: seed, KEY: hashlib.md5(raw.encode()).hexdigest()}

class SunloginAuth(AuthBase):
    """Attaches HTTP Pizza Authentication to the given Request object."""
    def __init__(self, password):
        # setup any auth-related data here
        self.password = password

    def __call__(self, r):
        # modify and return the request
        r.headers[HEAD_AUTH] = f"{AUTH_SUFFIX} {self.password}"
        return r


class HTTPRequest(ABC):
    hass = None
    session = None
    # requests timeout=None means "wait forever" and can hang the config
    # flow / refresh tasks for minutes; default to a sane bound.
    timeout = 30
    _verify = dict()
    _proxies = dict()

    @property
    def proxies(self):
        if (not self._proxies 
            or self._proxies.get('http') is None 
            or self._proxies.get('https') is None
        ):
            return None
        return self._proxies

    @proxies.setter
    def proxies(self, proxy):
        ssl_verify = False
        if not proxy:
            proxy = None
            ssl_verify = None

        self._proxies.update({'http': proxy, 'https': proxy})
        self.verify = ssl_verify

    @property
    def verify(self):
        return self._verify.get('verify')
    
    @verify.setter
    def verify(self, verify):
        if verify is None or verify:
            verify = None
        else:
            verify = False
        self._verify.update({'verify': verify})

    async def async_make_request_by_requests(self, method, url, data=None, headers=None, **kwargs):
        # session = self.session
        if method == "GET":
            func = functools.partial(
                self.session.get, 
                url,
                headers=headers, 
                params=data,
                verify=self.verify,
                timeout=self.timeout,
                proxies=self.proxies,
                **kwargs
            )
        elif method == "POST":
            func = functools.partial(
                self.session.post,
                url,
                headers=headers,
                json=data,
                verify=self.verify,
                timeout=self.timeout,
                proxies=self.proxies,
                **kwargs
            )
        elif method == "PUT":
            func = functools.partial(
                self.session.put,
                url,
                headers=headers,
                json=data,
                verify=self.verify,
                timeout=self.timeout,
                proxies=self.proxies,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp = await self.hass.async_add_executor_job(func)
        return resp

    def make_request_by_requests(self, method, url, data=None, headers=None):
        if headers is None:
            headers = {}
        if method == "GET":
            func = functools.partial(
                self.session.get, url, headers=headers, params=data
            )
        elif method == "POST":
            func = functools.partial(
                self.session.post,
                url,
                headers=headers,
                data=json.dumps(data),
            )
        elif method == "PUT":
            func = functools.partial(
                self.session.put,
                url,
                headers=headers,
                data=json.dumps(data),
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp = func()
        return resp


class CloudAPI(HTTPRequest):
    def __init__(self, hass, client_id=None):
        self.hass = hass
        self.client_id = client_id
        self.session = requests.Session()

    @property
    def headers(self):
        """Standard headers with the persisted client id (when set).

        Mirrors the official client _createHeaders(): both KAL-ClientID
        and ex-clientid are sent.
        """
        headers = base_headers()
        if self.client_id:
            headers[HEAD_KAL_CLIENT_ID] = self.client_id
            headers[HEAD_CLIENT_ID] = self.client_id
        return headers

    async def async_login_by_password(self, username, password):
        data = {
            "loginname" : username,
            "account" : username,
            "terminal_name" : TERMINAL_NAME,
            "type" : PASSWORD,
            "ismd5" : True,
            "password" : hashlib.md5(password.encode()).hexdigest(),
        }
        resp = await self.async_make_request_by_requests("POST", LOGIN_URL, data=data, headers=self.headers)

        #error
        return resp

    async def async_login_by_sms(self, username, smscode):
        data = {
            "loginname" : username,
            "account" : username,
            "terminal_name" : TERMINAL_NAME,
            "type" : SMS,
            "medium" : "sms",
            "code" : smscode,
        }

        resp = await self.async_make_request_by_requests("POST", LOGIN_URL, data=data, headers=self.headers)
        return resp

    async def async_refresh_token(self, access_token, refresh_token):
        data = {"access_token": access_token, "refresh_token": refresh_token}

        resp = await self.async_make_request_by_requests("POST", REFRESH_URL_V1, data=data, headers=self.headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_auth_code(self):
        resp = await self.async_make_request_by_requests("GET", AUTH_CODE_URL, headers=self.headers)
        return resp

    async def async_grant_auth_code(self, access_token, code):
        data = {"action": "grant", "code": code}

        resp = await self.async_make_request_by_requests("POST", AUTH_CODE_URL, data=data, headers=self.headers, auth=SunloginAuth(access_token))
        return resp

    async def async_login_terminals_by_code(self, access_token, code, mac="", code_origin='qrcode'):
        data = {"code": code, "mac": mac, "terminal_name": TERMINAL_NAME, "type": code_origin}

        resp = await self.async_make_request_by_requests("POST", LOGIN_TERMINALS_URL, data=data, headers=self.headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_devices_list(self, access_token):
        resp = await self.async_make_request_by_requests("GET", DEVICES_URL, headers=self.headers, auth=SunloginAuth(access_token))
        return resp

    async def async_send_verify_code(self, account, method):
        """Send a verify code for new-device login (POST /login-terminals/sendcode).

        method: VERIFY_METHOD_MOBILE or VERIFY_METHOD_EMAIL.
        """
        data = {"account": account, "method": method}
        resp = await self.async_make_request_by_requests(
            "POST", LOGIN_TERMINALS_SENDCODE_URL, data=data, headers=self.headers
        )
        return resp

    async def async_check_verify_code(self, account, method, code, terminal_name=TERMINAL_NAME):
        """Check the verify code for new-device login (PUT /login-terminals/checkcode).

        On success the response body directly contains the token info
        (access_token / refresh_token), same shape as /authorization.
        """
        data = {
            "account": account,
            "method": method,
            "code": code,
            "memo": "",
            "terminal_name": terminal_name,
        }
        resp = await self.async_make_request_by_requests(
            "PUT", LOGIN_TERMINALS_CHECKCODE_URL, data=data, headers=self.headers
        )
        return resp


class CloudAPI_V2(HTTPRequest):
    def __init__(self, hass):
        self.hass = hass
        self.session = requests.Session()

    async def async_get_qrdata(self):
        #https://user-api-v2.oray.com/qrcode/apply?account=171********&_t=1614407645711
        resp = await self.async_make_request_by_requests("GET", QRCODE_APPLY_URL, data={"_t": int(time.time()*1000)})
        
        return resp

    async def async_get_qrstatus(self, key):
        resp = await self.async_make_request_by_requests("GET", QRCODE_STATUS_URL, data={"_t": int(time.time()*1000), "key": key})

        return resp

    async def async_login_by_qrcode(self, secret):
        data = {"key":secret, "issetcookie":True}
        resp = await self.async_make_request_by_requests("POST", QRCODE_URL, data=data)

        return resp
    
    async def async_refresh_token(self, s_id):
        data = {"_t": int(time.time()*1000), "key": s_id}
        resp = await self.async_make_request_by_requests("GET", REFRESH_URL_V2, data=data)

        return resp
    


class PlugAPI_V1(HTTPRequest):
    _address = None
    
    def __init__(self, hass, address):
        self.hass = hass
        self.address = address
        self.session = requests.Session()

    @property
    def address(self):
        return self._address + PLUG_PATH
    
    @address.setter
    def address(self, address):
        self._address = address
    
    def calc_key(self, sn):
        # return calc_key_with_str(sn)
        return calc_key_with_time(sn)

    async def async_get_status(self, sn):
        data = {API: API_GET_STATUS}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_get_electric(self, sn):
        #https://sl-api.oray.com/smartplugs/{sn}/electric-online
        data = {API: API_GET_PLUG_ELECTRIC}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_get_info(self, sn):
        data = {API: API_GET_PLUG_INFO}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_get_sn(self, sn='sunlogin'):
        data = {API: API_GET_SN}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_get_wifi_info(self, sn):
        data = {API: API_GET_WIFI_INFO}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_set_status(self, sn, index, status):
        data = {API: API_SET_STATUS, "index": index, "status": status}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_set_led(self, sn, status):
        data = {API: API_SET_PLUG_LED, "enabled": status}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp

    async def async_set_default(self, sn, status):
        data = {API: API_SET_PLUG_DFLTSTAT, "default": status*2}
        data.update(self.calc_key(sn))

        resp = await self.async_make_request_by_requests("GET", self.address, data=data)
        return resp
    
    async def async_add_timer(self, sn, timer):
        #{"time": 2023, "repeat": 0, "enable": 1, "action": 0}
        #%257B%2522time%2522%253A2023%252C%2522repeat%2522%253A0%252C%2522enable%2522%253A1%252C%2522action%2522%253A0%257D
        #%7B%22time%22%3A2023%2C%22repeat%22%3A0%2C%22enable%22%3A1%2C%22action%22%3A0%7D
        pass

    async def async_get_power_consumes(self, sn, index=0, access_token=None):
        url = f"https://sl-api.oray.com/smartplug/powerconsumes/{sn}?index={index}"

        auth = SunloginAuth(access_token) if access_token else None
        resp = await self.async_make_request_by_requests("GET", url, auth=auth)
        return resp
    


class PlugAPI_V2(HTTPRequest):
    _address = None
    
    def __init__(self, hass, address):
        self.hass = hass
        self.address = address
        # self._address = HTTPS_SUFFIX + '47.111.169.221' + PLUG_PATH
        self.session = requests.Session()

    @property
    def address(self):
        return self._address + PLUG_PATH
    
    @address.setter
    def address(self, address):
        self._address = address
    
    def calc_key(self, sn):
        # return calc_key_with_str(sn)
        return calc_key_with_time(sn)

    async def async_get_status(self, sn, access_token):
        data = {API: API_GET_STATUS, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_electric(self, sn, access_token):
        #https://sl-api.oray.com/smartplugs/{sn}/electric-online
        data = {API: API_GET_PLUG_ELECTRIC, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_info(self, sn, access_token):
        data = {API: API_GET_PLUG_INFO, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_sn(self, sn='sunlogin', access_token='a'):
        data = {API: API_GET_SN, SN: sn}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_wifi_info(self, sn, access_token):
        data = {API: API_GET_WIFI_INFO, SN: sn}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_status(self, sn, index, status, access_token):
        data = {API: API_SET_STATUS, SN: sn, "index": index, "status": status}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_led(self, sn, status, access_token):
        data = {API: API_SET_PLUG_LED, SN: sn, "enabled": status}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_default(self, sn, status, access_token):
        data = {API: API_SET_PLUG_DFLTSTAT, SN: sn, "default": status*2}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}

        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp
    
    async def async_add_timer(self, sn, timer, access_token):
        #{"time": 2023, "repeat": 0, "enable": 1, "action": 0}
        #%257B%2522time%2522%253A2023%252C%2522repeat%2522%253A0%252C%2522enable%2522%253A1%252C%2522action%2522%253A0%257D
        #%7B%22time%22%3A2023%2C%22repeat%22%3A0%2C%22enable%22%3A1%2C%22action%22%3A0%7D
        pass

    async def async_get_power_consumes(self, sn, index=0, access_token=None):
        url = f"https://sl-api.oray.com/smartplug/powerconsumes/{sn}?index={index}"

        auth = SunloginAuth(access_token) if access_token else None
        resp = await self.async_make_request_by_requests("GET", url, auth=auth)
        return resp
    

class PlugAPI_V2_FAST(HTTPRequest):
    _address = None
    _process_address = dict()

    def __init__(self, hass, address):
        self.hass = hass
        self._address = address
        # self._address = HTTPS_SUFFIX + '47.111.169.221' + PLUG_PATH
        self.adapters = dict()
        self.session = requests.Session()

    @property
    def address(self):
        address = self._process_address[self._address]
        return address + PLUG_PATH
    
    @address.setter
    def address(self, address):
        self._address = address
        if self._process_address.get(address) is None:
            self._process_address[address] = address    
    
    def calc_key(self, sn):
        # return calc_key_with_str(sn)
        return calc_key_with_time(sn)
    
    def process_address(self, address):
        if self._process_address.get(address) is None:
            self._process_address[address] = address          

    def process_cert(self):
        address = self._process_address[self._address]
        if address != self._address and self.adapters.get(address) is None:
            adapter = HTTPAdapter()
            self.adapters[address] = adapter
            connection_pool_kwargs = adapter.poolmanager.connection_pool_kw
            connection_pool_kwargs['assert_hostname'] = PLUG_DOMAIN
            self.session.mount(address, adapter)
            
    async def async_get_status(self, sn, access_token):
        data = {API: API_GET_STATUS, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_electric(self, sn, access_token):
        #https://sl-api.oray.com/smartplugs/{sn}/electric-online
        data = {API: API_GET_PLUG_ELECTRIC, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_info(self, sn, access_token):
        data = {API: API_GET_PLUG_INFO, SN: sn}
        data.update(self.calc_key(sn))

        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_sn(self, sn='sunlogin', access_token='a'):
        data = {API: API_GET_SN, SN: sn}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_get_wifi_info(self, sn, access_token):
        data = {API: API_GET_WIFI_INFO, SN: sn}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_status(self, sn, index, status, access_token):
        data = {API: API_SET_STATUS, SN: sn, "index": index, "status": status}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_led(self, sn, status, access_token):
        data = {API: API_SET_PLUG_LED, SN: sn, "enabled": status}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp

    async def async_set_default(self, sn, status, access_token):
        data = {API: API_SET_PLUG_DFLTSTAT, SN: sn, "default": status*2}
        data.update(self.calc_key(sn))
        
        headers = {'Host': PLUG_DOMAIN}
        self.process_cert()
        resp = await self.async_make_request_by_requests("GET", self.address, data=data, headers=headers, auth=SunloginAuth(access_token))
        return resp
    
    async def async_add_timer(self, sn, timer, access_token):
        #{"time": 2023, "repeat": 0, "enable": 1, "action": 0}
        #%257B%2522time%2522%253A2023%252C%2522repeat%2522%253A0%252C%2522enable%2522%253A1%252C%2522action%2522%253A0%257D
        #%7B%22time%22%3A2023%2C%22repeat%22%3A0%2C%22enable%22%3A1%2C%22action%22%3A0%7D
        pass

    async def async_get_power_consumes(self, sn, index=0, access_token=None):
        url = f"https://sl-api.oray.com/smartplug/powerconsumes/{sn}?index={index}"
        
        auth = SunloginAuth(access_token) if access_token else None
        resp = await self.async_make_request_by_requests("GET", url, auth=auth)
        return resp
    

    