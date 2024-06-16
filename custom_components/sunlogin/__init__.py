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
    EVENT_HOMEASSISTANT_STOP,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval

from .sunlogin import SunLogin, Token, PlugConfigUpdateManager, DNSUpdateManger, get_sunlogin_device
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
    # username = user_input[CONF_USERNAME]
    # password = user_input[CONF_PASSWORD]
    # smscode = user_input[CONF_SMSCODE]
    # cloud_api = SunLogin(hass, username, password, smscode)
    _LOGGER.debug(entry.entry_id)
    _LOGGER.debug(entry.data)
    token = Token(hass)
    config_update = PlugConfigUpdateManager(hass)
    dns_update = DNSUpdateManger(hass)
    config = {
        SL_DEVICES: list(),
        CONF_TOKEN: token,
        CONF_REQUESTS_SESSION: None,
        CONF_CONFIGURATION_UPDATE: config_update,
    }
    hass.data[DOMAIN][CONFIG][entry.entry_id] = config
    hass.data[DOMAIN][CONF_SCAN_INTERVAL] = entry.data[CONF_USER_INPUT][CONF_SCAN_INTERVAL]
    hass.data[DOMAIN][CONF_DNS_UPDATE] = dns_update
    token.setup(entry.data.get(CONF_ACCESS_TOKEN), entry.data.get(CONF_REFRESH_TOKEN), entry.data.get(CONF_REFRESH_EXPIRE, time.time()))
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

        
        await token.coordinator.async_config_entry_first_refresh()
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
    pass

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
