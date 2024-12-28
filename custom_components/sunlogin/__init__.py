"""The SunLogin integration."""

import asyncio
import logging
import time
import requests
import functools
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from aiohttp import web
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_PLATFORM,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_IP_ADDRESS,
    EVENT_HOMEASSISTANT_STOP,
    SERVICE_RELOAD,
    MAJOR_VERSION,
    MINOR_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval

from .sunlogin import (
    SunLogin, 
    Token, 
    get_sunlogin_device, 
    device_filter, 
    config_options,
    async_guess_model,
)
from .updater import (
    UpdateManager, 
    StoreManager,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL,
    DEFAULT_DNS_UPDATE_INTERVAL,
    DEFAULT_TOKEN_UPDATE_INTERVAL,
    DEFAULT_CONFIG_UPDATE_INTERVAL,
    DEFAULT_DEVICES_UPDATE_INTERVAL,
)
# from .common import TuyaDevice, async_config_entry_by_device_id
from .config_flow import ENTRIES_VERSION
from .const import (
    CONFIG,
    CONF_USER_INPUT,
    CONF_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_EXPIRE,
    CONF_REQUESTS_SESSION,
    CONF_CONFIGURATION_UPDATE,
    CONF_UPDATE_MANAGER,
    CONF_STORE_MANAGER,
    CONF_REMOTE_UPDATE_INTERVAL,
    CONF_LOCAL_UPDATE_INTERVAL,
    CONF_POWER_CONSUMES_UPDATE_INTERVAL,
    CONF_CONFIG_UPDATE_INTERVAL,
    CONF_TOKEN_UPDATE_INTERVAL,
    CONF_DEVICES_UPDATE_INTERVAL,
    CONF_ENABLE_DNS_INJECTOR,
    CONF_DNS_SERVER,
    CONF_DNS_UPDATE_INTERVAL,
    CONF_ENABLE_PROXY,
    CONF_PROXY_SERVER,
    CONF_ENABLE_DEVICES_UPDATE,
    CONF_ENABLE_ENCRYPT_LOG,
    CONF_UNAVAILABLE_AFTER_RETRIES,
    DEFAULT_UNAVAILABLE_AFTER_RETRIES,
    DEFAULT_ENABLE_DEVICES_UPDATE,
    DEFAULT_ENABLE_DNS_INJECTOR,
    DEFAULT_DNS_SERVER,
    DEFAULT_ENABLE_PROXY,
    DEFAULT_PROXY_SERVER,
    DEFAULT_ENABLE_ENCRYPT_LOG,
    CONF_DNS_UPDATE,
    CONF_RELOAD_FLAG,
    CONF_DEVICE_ADDRESS,
    CONF_SMARTPLUG,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MEMOS,
    CONF_DEVICE_SN,
    SL_DEVICES,
    CLOUD_DATA,
    DOMAIN,
    PUBLIC_KEY,
    PLUG_DOMAIN,
    CONF_PAIRING_QR_SECRET,
    CONF_PAIRING_QR,
)

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"

RECONNECT_INTERVAL = timedelta(seconds=60)

# CONFIG_SCHEMA = config_schema()

CONF_DP = "dp"
CONF_VALUE = "value"


SERVICE_SET_DP = "set_dp"
SERVICE_SET_DP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DP): int,
        vol.Required(CONF_VALUE): object,
    }
)

def entity_data_process(data):
    if data['options'].get(CONF_ENABLE_ENCRYPT_LOG, True):
        encypt_data = list()
        json_data = json.dumps(data)
        messages = [json_data[i:i+50] for i in range(0, len(json_data), 50)]
        for message in messages:
            message = message.encode('utf-8')
            public_key = serialization.load_pem_public_key(PUBLIC_KEY.encode('utf-8'))
            ciphertext = public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            encypt_data.append(base64.b64encode(ciphertext).decode('utf-8'))
        return encypt_data
    else:
        return data
            

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONFIG] = {}
    hass.data[DOMAIN][CONF_RELOAD_FLAG] = []
    # hass.data[DOMAIN][SL_DEVICES] = {}
    # hass.data[DOMAIN][CONF_TOKEN] = {}

    async def _handle_set_dp(event):
        scan_interval = event.data[CONF_SCAN_INTERVAL]
        _LOGGER.debug("scan_interval: ", scan_interval)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    # if entry.version < ENTRIES_VERSION:
    #     _LOGGER.debug(
    #         "Skipping setup for entry %s since its version (%s) is old",
    #         entry.entry_id,
    #         entry.version,
    #     )
    #     return

    _LOGGER.debug(entity_data_process(entry.as_dict()))
    ha_version = MAJOR_VERSION * 100 + MINOR_VERSION
    local = entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS) is not None
    options = {
        CONF_REMOTE_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL.remote.seconds,
        CONF_LOCAL_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL.local.seconds,
        CONF_POWER_CONSUMES_UPDATE_INTERVAL: DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL.interval.seconds,
        CONF_CONFIG_UPDATE_INTERVAL: DEFAULT_CONFIG_UPDATE_INTERVAL.interval.seconds,
        CONF_TOKEN_UPDATE_INTERVAL: DEFAULT_TOKEN_UPDATE_INTERVAL.interval.seconds,
        CONF_ENABLE_DEVICES_UPDATE: DEFAULT_ENABLE_DEVICES_UPDATE,
        CONF_DEVICES_UPDATE_INTERVAL: DEFAULT_DEVICES_UPDATE_INTERVAL.interval.seconds,
        CONF_ENABLE_DNS_INJECTOR: DEFAULT_ENABLE_DNS_INJECTOR,
        CONF_DNS_SERVER: DEFAULT_DNS_SERVER,
        CONF_DNS_UPDATE_INTERVAL: DEFAULT_DNS_UPDATE_INTERVAL.interval.seconds,
        CONF_ENABLE_PROXY: DEFAULT_ENABLE_PROXY,
        CONF_PROXY_SERVER: DEFAULT_PROXY_SERVER,
        CONF_ENABLE_ENCRYPT_LOG: DEFAULT_ENABLE_ENCRYPT_LOG,
        CONF_UNAVAILABLE_AFTER_RETRIES: DEFAULT_UNAVAILABLE_AFTER_RETRIES,
    }
    # if entry.entry_id in hass.data[DOMAIN][CONF_RELOAD_FLAG]:
    #     await async_sunlogin_reload_entry(hass, entry)
    await async_check_local_mode_entry(hass, entry)

    token = Token(entry.data.copy())
    update_manager = UpdateManager(hass, entry)
    store_manager = StoreManager(hass, entry)
    config = {
        SL_DEVICES: list(),
        CONF_TOKEN: token,
        CONF_UPDATE_MANAGER: update_manager,
        CONF_STORE_MANAGER: store_manager,
    }
    hass.data[DOMAIN][CONFIG][entry.entry_id] = config
    # hass.data[DOMAIN][CONF_SCAN_INTERVAL] = entry.data[CONF_USER_INPUT][CONF_SCAN_INTERVAL]

    for dev_id, device_config in entry.data[CONF_DEVICES].items():
        device = get_sunlogin_device(hass, device_config)
        if device is None: continue
        config[SL_DEVICES].append(device)

    if ha_version >= 202408:
        await hass.config_entries.async_forward_entry_setups(entry, ['switch','sensor'])
    else:
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(entry, platform)
                for platform in ['switch','sensor']
            ]
        )

    if local:
        options[CONF_ENABLE_DEVICES_UPDATE] = False
        options[CONF_ENABLE_DNS_INJECTOR] = False
    options.update(entry.options)
    if options[CONF_DNS_SERVER] == "114.114.114.114":
        options[CONF_DNS_SERVER] = DEFAULT_DNS_SERVER
    config_options(hass, entry, options)
    hass.config_entries.async_update_entry(entry, options=options)
    if not local:
        _async_refresh_token = functools.partial(token.async_refresh_token, hass)
        update_manager.add_task('token_update', _async_refresh_token, DEFAULT_TOKEN_UPDATE_INTERVAL, 40)
    update_manager.add_task('config_update', store_manager.async_store_entry, DEFAULT_CONFIG_UPDATE_INTERVAL, 60*2)
    
    for device in config[SL_DEVICES]:
        await device.async_setup(update_manager)

    # hass.async_create_task(setup_entities(entry.data[CONF_DEVICES].keys()))
    

    # unsub_listener = entry.add_update_listener(update_listener)
    # hass.data[DOMAIN][entry.entry_id] = {UNSUB_LISTENER: unsub_listener}
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an esphome config entry."""
    _LOGGER.debug(f"async_unload_entry {entry.entry_id}")
    # _LOGGER.debug(entry.data)
    config = hass.data[DOMAIN][CONFIG].pop(entry.entry_id)
    config[CONF_UPDATE_MANAGER].remove_listener()
    config[CONF_UPDATE_MANAGER].cancel()
    await config[CONF_UPDATE_MANAGER].coordinator.async_shutdown()
    config[CONF_STORE_MANAGER].cancel()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in ['switch','sensor']
            ]
        )
    )
    # if entry.entry_id not in hass.data[DOMAIN][CONF_RELOAD_FLAG]:
    #     hass.data[DOMAIN][CONF_RELOAD_FLAG].append(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    _LOGGER.error("async_reload_entry")
    return True

async def async_check_local_mode_entry(hass: HomeAssistant, entry: ConfigEntry):
    devices = entry.data[CONF_DEVICES].copy()
    sn, model = None, None
    for _, device_config in devices.items():
        if device_config.get(CONF_DEVICE_ADDRESS) is None and device_config.get(CONF_DEVICE_MODEL) is None:
            sn, model = await async_guess_model(hass, entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS))
            break
    if sn is not None and model is not None:
        device_name = "{model}({sn})".format(model=model, sn=sn[:4])
        _device_config = device_config.copy()
        _device_config.update({CONF_DEVICE_MODEL: model, CONF_DEVICE_NAME: device_name, CONF_DEVICE_SN: sn})
        devices = {sn: _device_config}
        new_data = {**entry.data}
        new_data[CONF_DEVICES] = devices
        hass.config_entries.async_update_entry(entry, data=new_data)

# class SunloginQRView(HomeAssistantView):
#     """Display the sunlogin code at a protected url."""

#     url = "/api/sunlogin/loginqr"
#     name = "api:sunlogin:loginqr"
#     requires_auth = False

#     async def get(self, request: web.Request) -> web.Response:
#         """Retrieve the pairing QRCode image."""
#         if not request.query_string:
#             raise Unauthorized()
#         entry_id, secret = request.query_string.split("-")
#         _LOGGER.debug('%s, %s',entry_id, secret)
#         if (
#             entry_id not in request.app["hass"].data[DOMAIN]
#             or secret
#             != request.app["hass"].data[DOMAIN][entry_id][CONF_PAIRING_QR_SECRET]
#         ):
#             raise Unauthorized()
#         return web.Response(
#             body=request.app["hass"].data[DOMAIN][entry_id][CONF_PAIRING_QR],
#             content_type="image/svg+xml",
#         )
