"""The SunLogin integration."""

import asyncio
import logging
import functools
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICES,
    CONF_IP_ADDRESS,
    MAJOR_VERSION,
    MINOR_VERSION,
)
from homeassistant.core import HomeAssistant

from .sunlogin import (
    Token,
    get_sunlogin_device,
    config_options,
    async_guess_model,
)
from .sunlogin_api import DEFAULT_USER_AGENT
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

from .const import (
    CONFIG,
    CONF_USER_INPUT,
    CONF_TOKEN,
    CONF_CLIENT_ID,
    CONF_UPDATE_MANAGER,
    CONF_STORE_MANAGER,
    CONF_REMOTE_UPDATE_INTERVAL,
    CONF_LOCAL_UPDATE_INTERVAL,
    CONF_POWER_CONSUMES_UPDATE_INTERVAL,
    CONF_CONFIG_UPDATE_INTERVAL,
    CONF_TOKEN_UPDATE_INTERVAL,
    CONF_DEVICES_UPDATE_INTERVAL,
    CONF_ENABLE_DEVICES_UPDATE,
    CONF_ENABLE_DNS_INJECTOR,
    CONF_DNS_SERVER,
    CONF_DNS_UPDATE_INTERVAL,
    CONF_ENABLE_PROXY,
    CONF_PROXY_SERVER,
    CONF_ENABLE_ENCRYPT_LOG,
    CONF_UNAVAILABLE_AFTER_RETRIES,
    CONF_USER_AGENT,
    DEFAULT_UNAVAILABLE_AFTER_RETRIES,
    DEFAULT_ENABLE_DEVICES_UPDATE,
    DEFAULT_ENABLE_DNS_INJECTOR,
    DEFAULT_DNS_SERVER,
    DEFAULT_ENABLE_PROXY,
    DEFAULT_PROXY_SERVER,
    DEFAULT_ENABLE_ENCRYPT_LOG,
    CONF_OPTIONS_VERSION,
    CONF_RELOAD_FLAG,
    CONF_DEVICE_ADDRESS,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SN,
    SL_DEVICES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"

RECONNECT_INTERVAL = timedelta(seconds=60)

DEFAULT_OPTIONS = {
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

def global_config(hass: HomeAssistant, entry: ConfigEntry):
    token = Token(entry.data.copy(), entry.data.get(CONF_CLIENT_ID))
    update_manager = UpdateManager(hass, entry)
    store_manager = StoreManager(hass, entry)
    config = {
        SL_DEVICES: list(),
        CONF_TOKEN: token,
        CONF_UPDATE_MANAGER: update_manager,
        CONF_STORE_MANAGER: store_manager,
    }
    return config, token, update_manager, store_manager
            

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the SunLogin integration component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONFIG] = {}
    hass.data[DOMAIN][CONF_RELOAD_FLAG] = []

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up SunLogin integration from a config entry."""
    ha_version = MAJOR_VERSION * 100 + MINOR_VERSION
    local = entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS) is not None
    options = DEFAULT_OPTIONS.copy()
    await async_check_local_mode_entry(hass, entry)

    config, token, update_manager, store_manager = global_config(hass, entry)
    hass.data[DOMAIN][CONFIG][entry.entry_id] = config

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
    OPTIONS_VERSION = 307
    if options.get(CONF_OPTIONS_VERSION, 100) < OPTIONS_VERSION:
        options[CONF_TOKEN_UPDATE_INTERVAL] = 299
        options[CONF_OPTIONS_VERSION] = OPTIONS_VERSION
        # apply the (possibly changed) default User-Agent on upgrade
        if options.get(CONF_USER_AGENT) is None:
            options[CONF_USER_AGENT] = DEFAULT_USER_AGENT
    config_options(hass, entry, options)
    hass.config_entries.async_update_entry(entry, options=options)
    if not local:
        _async_refresh_token = functools.partial(token.async_refresh_token, hass)
        update_manager.add_task('token_update', _async_refresh_token, DEFAULT_TOKEN_UPDATE_INTERVAL, 40)
    update_manager.add_task('config_update', store_manager.async_store_entry, DEFAULT_CONFIG_UPDATE_INTERVAL, 60*2)
    
    for device in config[SL_DEVICES]:
        await device.async_setup(update_manager)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a sunlogin config entry."""
    _LOGGER.debug("async_unload_entry %s", entry.entry_id)
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
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    _LOGGER.debug("async_reload_entry %s", entry.entry_id)


async def async_check_local_mode_entry(hass: HomeAssistant, entry: ConfigEntry):
    devices = entry.data[CONF_DEVICES].copy()
    sn, model = None, None
    device_config = None
    for _, device_config in devices.items():
        if device_config.get(CONF_DEVICE_ADDRESS) is None and device_config.get(CONF_DEVICE_MODEL) is None:
            sn, model = await async_guess_model(hass, entry.data[CONF_USER_INPUT].get(CONF_IP_ADDRESS))
            break
    if sn is not None and model is not None and device_config is not None:
        device_name = "{model}({sn})".format(model=model, sn=sn[:4])
        _device_config = device_config.copy()
        _device_config.update({CONF_DEVICE_MODEL: model, CONF_DEVICE_NAME: device_name, CONF_DEVICE_SN: sn})
        devices = {sn: _device_config}
        new_data = {**entry.data}
        new_data[CONF_DEVICES] = devices
        hass.config_entries.async_update_entry(entry, data=new_data)

