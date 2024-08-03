"""The SunLogin integration."""

import asyncio
import logging
import time
import requests
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
)
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval

from .sunlogin import SunLogin, Token, TokenUpdateManger, PlugConfigUpdateManager, DNSUpdateManger, get_sunlogin_device, device_filter, guess_model
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

    # user_input = entry.data['user_input']
    _LOGGER.debug(entry.entry_id)
    _LOGGER.debug(entry.data)
    _LOGGER.debug(hass.data[DOMAIN][CONF_RELOAD_FLAG])
    if entry.entry_id in hass.data[DOMAIN][CONF_RELOAD_FLAG]:
        await async_sunlogin_reload_entry(hass, entry)
    await async_check_local_mode_entry(hass, entry)

    token_update = TokenUpdateManger(hass)
    config_update = PlugConfigUpdateManager(hass)
    dns_update = DNSUpdateManger(hass)
    config = {
        SL_DEVICES: list(),
        CONF_TOKEN: token_update,
        CONF_REQUESTS_SESSION: None,
        CONF_CONFIGURATION_UPDATE: config_update,
    }
    hass.data[DOMAIN][CONFIG][entry.entry_id] = config
    hass.data[DOMAIN][CONF_SCAN_INTERVAL] = entry.data[CONF_USER_INPUT][CONF_SCAN_INTERVAL]
    hass.data[DOMAIN][CONF_DNS_UPDATE] = dns_update
    token = Token(entry.data.copy())
    token_update.setup(token)
    dns_update.dns.set_domain(PLUG_DOMAIN)
    dns_update.devices = config[SL_DEVICES]
    config_update.devices = config[SL_DEVICES]

    async def setup_entities(device_ids):
        for dev_id in device_ids:
            device_config = entry.data[CONF_DEVICES][dev_id]
            device = get_sunlogin_device(hass, device_config)
            if device is None: continue
            config[SL_DEVICES].append(device)
            # await device.async_setup()


        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(entry, platform)
                for platform in ['switch','sensor']
            ]
        )

        
        await token_update.coordinator.async_config_entry_first_refresh()
        await dns_update.coordinator.async_config_entry_first_refresh()
        for device in config[SL_DEVICES]:
            await device.async_setup()
        # await config_update.coordinator.async_config_entry_first_refresh()
        #await hass.config_entries.async_reload(entry.entry_id)

    
    hass.async_create_task(setup_entities(entry.data[CONF_DEVICES].keys()))
    

    # unsub_listener = entry.add_update_listener(update_listener)
    # hass.data[DOMAIN][entry.entry_id] = {UNSUB_LISTENER: unsub_listener}
    hass.data[DOMAIN]['random'] = 'ootd'
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an esphome config entry."""
    _LOGGER.debug("async_unload_entry")
    _LOGGER.debug(entry.entry_id)
    _LOGGER.debug(entry.data)
    config = hass.data[DOMAIN][CONFIG].pop(entry.entry_id)
    for device in config[SL_DEVICES]:
        await device.update_manager.coordinator.async_shutdown()
    await config[CONF_TOKEN].coordinator.async_shutdown()
    await config[CONF_CONFIGURATION_UPDATE].coordinator.async_shutdown()
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in ['switch','sensor']
            ]
        )
    )
    if entry.entry_id not in hass.data[DOMAIN][CONF_RELOAD_FLAG]:
        hass.data[DOMAIN][CONF_RELOAD_FLAG].append(entry.entry_id)
    return unload_ok

async def async_check_local_mode_entry(hass: HomeAssistant, entry: ConfigEntry):
    devices = entry.data[CONF_DEVICES].copy()
    sn, model = None, None
    for _, device_config in devices.items():
        if device_config.get(CONF_DEVICE_ADDRESS) is None and device_config.get(CONF_DEVICE_MODEL) is None:
            sn, model = await guess_model(hass, entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS))
            break
    if sn is not None and model is not None:
        device_name = "{model}({sn})".format(model=model, sn=sn[:4])
        _device_config = device_config.copy()
        _device_config.update({CONF_DEVICE_MODEL: model, CONF_DEVICE_NAME: device_name, CONF_DEVICE_SN: sn})
        devices = {sn: _device_config}
        new_data = {**entry.data}
        new_data[CONF_DEVICES] = devices
        hass.config_entries.async_update_entry(entry, data=new_data)



async def async_sunlogin_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS) is not None:
        hass.data[DOMAIN][CONF_RELOAD_FLAG].remove(entry.entry_id)
        return

    new_data = {**entry.data}
    update_flag = False

    sunlogin = SunLogin(hass)
    sunlogin.token.set_token(entry.data)
    result = await sunlogin.check_and_refresh()
    if result:
        update_flag = True
        new_data.update(sunlogin.token.get_token())
    elif result is None:
        pass
    
    await sunlogin.async_get_devices_list()
    devices = device_filter(sunlogin.device_list)
    for sn, dev in devices.items():
        device = new_data[CONF_DEVICES].get(sn)
        if device is None:
            update_flag = True
            new_data[CONF_DEVICES][sn] = dev
        elif (
            str(device.get(CONF_DEVICE_NAME)) != str(dev.get(CONF_DEVICE_NAME)) 
            or str(device.get(CONF_DEVICE_MEMOS)) != str(dev.get(CONF_DEVICE_MEMOS))
        ):
            update_flag = True
            new_data[CONF_DEVICES][sn].update(dev)
    
    if update_flag:
        hass.config_entries.async_update_entry(entry, data=new_data)

    hass.data[DOMAIN][CONF_RELOAD_FLAG].remove(entry.entry_id)
    _LOGGER.debug(entry.data)
    


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
