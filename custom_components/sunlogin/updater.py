import logging
import uuid
from datetime import timedelta, datetime, timezone
from dataclasses import dataclass
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed
)
from homeassistant.const import CONF_DEVICES
from homeassistant.util import dt as dt_util
from homeassistant import config_entries
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_MEMOS,
)

_LOGGER = logging.getLogger(__name__)

MIN_REMOTE_INTERVAL = 60
MIN_LOCAL_INTERVAL = 10

@dataclass
class UpdateInterval:
    _local: int = timedelta(seconds=MIN_LOCAL_INTERVAL)
    _remote: int = timedelta(seconds=MIN_REMOTE_INTERVAL)

    @property
    def local(self):
        return self._local
    
    @local.setter
    def local(self, value):
        if value <= MIN_LOCAL_INTERVAL:
            return
        self._local = timedelta(seconds=value)

    @property
    def remote(self):
        return self._remote
    
    @remote.setter
    def remote(self, value):
        if value <= MIN_REMOTE_INTERVAL:
            return
        self._remote = timedelta(seconds=value)

    def set(self, config):
        if (local := config.get('local')) is not None: 
            self.local = local
        if (remote := config.get('remote')) is not None:
            self.remote = remote


@dataclass
class PlugUpdateInterval:
    update_interval: UpdateInterval
    _interval: int

    @property
    def interval(self):
        if self._interval == 0:
            return self.update_interval.local
        elif self._interval == 1:
            return self.update_interval.remote
        else:
            return self.update_interval.remote
    
    @interval.setter
    def interval(self, value):
        self._interval = value
        
@dataclass
class GeneralUpdateInterval:
    _interval: timedelta

    def __init__(self, interval):
        self.interval = interval

    @property
    def interval(self):
        return self._interval
    
    @interval.setter
    def interval(self, value):
        self._interval = timedelta(seconds=value)


class StoreManager():
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.data = {**entry.data}
        self.flag = False
        self.reload_flag = False

    def update_device_config(self, sn, data):
        self.data[CONF_DEVICES][sn].update(data)
        self.flag = True

    def update_device(self, devices):
        for sn, new_dev in devices.items():
            old_dev = self.data[CONF_DEVICES].get(sn)
            if old_dev is None:
                self.data[CONF_DEVICES][sn] = new_dev
                self.flag = True
                self.reload_flag = True
                _LOGGER.debug(f"StoreManager({self.entry.entry_id}) new device added")
            elif (
                str(old_dev.get(CONF_DEVICE_NAME)) != str(new_dev.get(CONF_DEVICE_NAME)) 
                or str(old_dev.get(CONF_DEVICE_MEMOS)) != str(new_dev.get(CONF_DEVICE_MEMOS))
            ):
                self.data[CONF_DEVICES][sn].update(new_dev)
                self.flag = True
                self.reload_flag = True
                _LOGGER.debug(f"StoreManager({self.entry.entry_id}) device name updated")

    def update_token(self, data):
        self.data.update(data)
        self.flag = True

    def cancel(self):
        self.entry = None

    async def async_store_entry(self):
        if self.flag:
            self.hass.config_entries.async_update_entry(self.entry, data=self.data)
            self.flag = False
            _LOGGER.debug(f"StoreManager({self.entry.entry_id}) data write to entry")
        if self.reload_flag:
            self.hass.async_create_task(self.hass.config_entries.async_reload(self.entry.entry_id))
            self.reload_flag = False
            _LOGGER.debug(f"StoreManager({self.entry.entry_id}) devices write to entry")
    


class UpdateManager():

    _tick = None

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.id = str(uuid.uuid4())
        self.tick = 10
        self.tasks = {}
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="SunloginUpdateScheduler",
            update_method=self.execute_tasks,
            update_interval=self.tick,
        )
        self.remove_listener = self.coordinator.async_add_listener(self.nop)
    
    @property
    def tick(self):
        return self._tick
    
    @tick.setter
    def tick(self, value):
        self._tick = timedelta(seconds=value)

    def nop(self):
        """"""

    async def execute_tasks(self):
        current_time = dt_util.utcnow()

        for task_name, task_info in self.tasks.items():
            if task_info is None:
                continue
            if current_time >= task_info['next_run']:
                _LOGGER.debug(f"UpdateManager({self.entry.entry_id}) executing task {task_name}")
                # try:
                #     await task_info['task']()
                # except Exception as e:
                #     _LOGGER.error(f"UpdateManager({self.id}) execute_tasks {task_name} failed: {e}")
                # await task_info['task']()
                self.entry.async_create_background_task(self.hass, task_info['task'](), task_name)
                task_info['next_run'] = current_time + task_info['update_interval'].interval


    def add_task(self, task_name, task, update_interval, first_add=10):
        next_run = dt_util.utcnow() + timedelta(seconds=first_add)
        # if task_name in self.tasks:
        #     next_run = dt_util.utcnow() + update_interval.interval
        
        self.tasks[task_name] = {
            'task': task,
            'update_interval': update_interval,
            'next_run': next_run,
        }
        _LOGGER.debug(f"UpdateManager({self.entry.entry_id}) add_task {task_name} next_run: {next_run}")

    def del_task(self, task_name):
        if task_name in self.tasks:
            self.tasks[task_name] = None

    def clear_tasks(self):
        self.tasks = dict()
        _LOGGER.debug(f"UpdateManager({self.entry.entry_id}) clear_tasks")

    def cancel(self):
        self.clear_tasks()
        self.entry = None

DEFAULT_UPDATE_INTERVAL = UpdateInterval()
DEFAULT_POWER_CONSUMES_UPDATE_INTERVAL = GeneralUpdateInterval(1200)
DEFAULT_DNS_UPDATE_INTERVAL = GeneralUpdateInterval(3600*8)
DEFAULT_CONFIG_UPDATE_INTERVAL = GeneralUpdateInterval(90)
DEFAULT_TOKEN_UPDATE_INTERVAL = GeneralUpdateInterval(600)
DEFAULT_DEVICES_UPDATE_INTERVAL = GeneralUpdateInterval(180)