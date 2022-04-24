from asyncio import create_task
from logging import getLogger
from typing import Callable, Generic, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (CoordinatorEntity,
                                                      DataUpdateCoordinator)

from .ecoflow.local import PRODUCTS, command, has_extra, receive, send
from .ecoflow.local.client import EcoFlowLocalClient

CONF_PRODUCT = "product"
DOMAIN = "ecoflow"
_LOGGER = getLogger(__name__)
_PLATFORMS = {
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
}

_T = TypeVar("_T")


class DataPushCoordinator(Generic[_T], DataUpdateCoordinator[_T]):
    __lock = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, client: EcoFlowLocalClient, reqdata: bytes, parser: Callable[[bytes, int], _T], defval: _T = {}):
        super().__init__(
            hass, _LOGGER,
            name=entry.unique_id + "/" + name,
            update_method=self.__get_data,
        )
        self._debounced_refresh.cooldown = 2
        self.data = defval
        self.last_update_success = False
        self.__client = client
        self.__reqdata = reqdata
        self.__parser = parser
        self.__product = entry.data[CONF_PRODUCT]

    def async_set_updated_data(self, data: _T):
        if self.__lock:
            return
        return super().async_set_updated_data(data)

    def async_pushed_args(self, args: bytes):
        if self.__lock:
            return
        self.async_set_updated_data(self.__parser(args, self.__product))

    async def __get_data(self):
        self.__lock = True
        try:
            return self.__parser(await self.__client.request(self.__reqdata), self.__product)
        finally:
            self.__lock = False


class HassioEcoFlowClient:
    device_info_extra = None
    serial_extra = None
    __extra_connected = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.client = EcoFlowLocalClient(entry.data[CONF_HOST], _LOGGER)
        self.product: int = entry.data[CONF_PRODUCT]
        self.serial = entry.unique_id

        self.device_info_main = DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer="EcoFlow",
            model=PRODUCTS.get(self.product, None),
            name=entry.title,
        )

        self.pd = DataPushCoordinator[dict](
            hass, entry, "pd", self.client, send.get_pd(), receive.pd)
        # self.pd.update_interval = timedelta(seconds=5)
        self.bms_main = DataPushCoordinator[dict](
            hass, entry, "bms_main", self.client, send.get_bms_main(), receive.bms_main)
        self.inv = DataPushCoordinator(
            hass, entry, "inv", self.client, send.get_inv(), receive.inv)
        self.bms_extra = DataPushCoordinator(
            hass, entry, "bms_extra", self.client, send.get_bms_extra(), receive.bms_extra)
        self.dc_in_mode = DataPushCoordinator(
            hass, entry, "dc_in_mode", self.client, send.get_dc_in_mode(self.product), receive.dc_in_mode, None)
        self.fan_auto = DataPushCoordinator(
            hass, entry, "fan_auto", self.client, send.get_fan_auto(), receive.fan_auto, None)
        self.coordinators: dict[tuple, DataPushCoordinator] = {
            command.pd: self.pd,
            command.bms_main: self.bms_main,
            command.inv: self.inv,
            command.dc_in_mode(self.product): self.dc_in_mode,
            command.fan_auto: self.fan_auto,
        }

        self.client.connected_handler = self.__connected
        self.client.disconnected_handler = self.__disconnected
        self.client.received_handler = self.__received
        self.client.run()

        def pd_updated():
            if "sys_ver" in self.pd.data:
                self.device_info_main["sw_version"] = self.pd.data["sys_ver"]
            if self.__extra_connected != has_extra(self.product, self.pd.data.get("model", None)):
                self.__extra_connected = not self.__extra_connected
                if self.__extra_connected:
                    self.__connected_extra()
                else:
                    self.__disconnected_extra()

        def extra_updated():
            if self.device_info_extra is None:
                return
            if "sys_ver" in self.pd.data:
                self.device_info_extra["sw_version"] = self.bms_extra.data["sys_ver"]

        self.pd.async_add_listener(pd_updated)
        self.bms_extra.async_add_listener(extra_updated)

    async def close(self):
        await self.client.close()

    def request(self, data: bytes):
        return self.client.request(data)

    def __connected(self):
        async def f():
            for cmd in self.coordinators:
                try:
                    await self.coordinators[cmd].async_refresh()
                except:
                    pass
        create_task(f())

    def __connected_extra(self):
        async def f():
            try:
                data = receive.sn(await self.request(send.get_sn_extra()))
                self.serial_extra = data["serial"]
                model = self.device_info_main["model"]
                if model:
                    model += " Extra Battery"
                else:
                    model = "Extra Battery"
                self.device_info_extra = DeviceInfo(
                    identifiers={(DOMAIN, self.serial_extra)},
                    manufacturer="EcoFlow",
                    model=model,
                    name=f"{model} {self.serial_extra[-6:]}",
                    via_device=(DOMAIN, self.serial),
                )
                await self.bms_extra.async_refresh()
            except:
                self.__extra_connected = False
        create_task(f())

    def __disconnected(self):
        if self.pd._unsub_refresh:
            self.pd._unsub_refresh()
            self.pd._unsub_refresh = None
        if self.__extra_connected:
            self.__extra_connected = False
            self.__disconnected_extra()
        for co in self.coordinators.values():
            co.last_update_success = False
            for cb in co._listeners:
                cb()

    def __disconnected_extra(self):
        self.serial_extra = None
        self.device_info_extra = None
        self.bms_extra.last_update_success = False
        for cb in self.bms_extra._listeners:
            cb()

    def __received(self, cmd: tuple[int, int, int], args: bytes):
        if cmd in self.coordinators:
            self.coordinators[cmd].async_pushed_args(args)
        create_task(self.pd.async_request_refresh())


class EcoFlowEntity(Generic[_T], CoordinatorEntity[DataPushCoordinator[_T]]):
    def __init__(self, client: HassioEcoFlowClient, module: str):
        super().__init__(getattr(client, module))
        self._client = client
        self._is_extra = module == "bms_extra"
        if self._is_extra:
            self.__serial = client.serial_extra
            self._attr_name = client.device_info_extra["name"]
            self._attr_unique_id = client.serial_extra
        else:
            self.__serial = client.serial
            self._attr_name = client.device_info_main["name"]
            self._attr_unique_id = client.serial

    @property
    def available(self):
        if self._is_extra and self._client.serial_extra != self.__serial:
            return False
        return super().available

    @property
    def device_info(self):
        if self._is_extra:
            return self._client.device_info_extra
        return self._client.device_info_main


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    client = HassioEcoFlowClient(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = client
    hass.config_entries.async_setup_platforms(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    client: HassioEcoFlowClient = hass.data[DOMAIN].pop(entry.entry_id)
    await client.close()
    return True
