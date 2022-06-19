from datetime import timedelta
from typing import Any, Callable, TypeVar

import reactivex.operators as ops
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, Platform
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.device_registry import async_get as async_get_dr
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.util.dt import utcnow
from reactivex import Observable, Subject, throw
from reactivex.subject.replaysubject import ReplaySubject

from . import ecoflow as ef
from .ecoflow import receive
from .ecoflow.rxtcp import RxTcpAutoConnection

CONF_PRODUCT = "product"
DISCONNECT_TIME = timedelta(seconds=15)
DOMAIN = "ecoflow"

_PLATFORMS = {
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    # Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
}

_T = TypeVar("_T")


async def to_task(src: Observable[_T]):
    return await src


async def request(tcp: RxTcpAutoConnection, req: bytes, res: Observable[_T]) -> _T:
    t = to_task(res.pipe(
        ops.timeout(5, throw(TimeoutError())),
        ops.first(),
    ))
    tcp.write(req)
    return await t


class HassioEcoFlowClient:
    device_info_extra = None
    serial_extra = None
    __disconnected = None
    __extra_connected = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.tcp = RxTcpAutoConnection(entry.data[CONF_HOST], ef.PORT)
        self.product: int = entry.data[CONF_PRODUCT]
        self.serial = entry.unique_id
        self.diagnostics = dict[str, dict[str, Any]]()
        dr = async_get_dr(hass)

        self.device_info_main = DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer="EcoFlow",
            model=ef.PRODUCTS.get(self.product, None),
            name=entry.title,
        )
        if mac := entry.data.get(CONF_MAC, None):
            self.device_info_main["connections"] = {
                (CONNECTION_NETWORK_MAC, mac),
            }

        self.received = self.tcp.received.pipe(
            receive.merge_packet(),
            ops.map(receive.decode_packet),
            ops.share(),
        )
        self.pd = self.received.pipe(
            ops.filter(receive.is_pd),
            ops.map(lambda x: receive.parse_pd(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )
        self.ems = self.received.pipe(
            ops.filter(receive.is_ems),
            ops.map(lambda x: receive.parse_ems(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )
        self.inverter = self.received.pipe(
            ops.filter(receive.is_inverter),
            ops.map(lambda x: receive.parse_inverter(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )
        self.mppt = self.received.pipe(
            ops.filter(receive.is_mppt),
            ops.map(lambda x: receive.parse_mppt(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )
        self.extra = self.received.pipe(
            ops.filter(receive.is_extra),
            ops.map(lambda x: receive.parse_extra(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )

        self.disconnected = Subject[None]()
        self.extra_disconnected = Subject[None]()

        def _disconnected(*args):
            self.__disconnected = None
            self.tcp.reconnect()
            self.diagnostics.clear()
            self.extra_disconnected.on_next(None)
            self.disconnected.on_next(None)
            if self.__extra_connected:
                self.__extra_connected = False
                self.__disconnected_extra()
        _job = HassJob(_disconnected)

        def reset_timer(*args):
            if self.__disconnected:
                self.__disconnected()
            self.__disconnected = event.async_track_point_in_utc_time(
                hass,
                _job,
                utcnow().replace(microsecond=0) + (DISCONNECT_TIME + timedelta(seconds=1)),
            )

        def end_timer(ex=None):
            self.extra_disconnected.on_next(None)
            self.disconnected.on_next(None)
            if ex:
                self.extra_disconnected.on_error(ex)
                self.disconnected.on_error(ex)
            else:
                self.extra_disconnected.on_completed()
                self.disconnected.on_completed()
        self.received.subscribe(reset_timer, end_timer, end_timer)

        # self.pd = DataPushCoordinator[dict](
        #     hass, entry, "pd", self.client, send.get_pd(), receive.pd)
        # # self.pd.update_interval = timedelta(seconds=5)
        # self.bms_main = DataPushCoordinator[dict](
        #     hass, entry, "bms_main", self.client, send.get_bms_main(), receive.bms_main)
        # self.inv = DataPushCoordinator(
        #     hass, entry, "inv", self.client, send.get_inv(), receive.inv)
        # self.bms_extra = DataPushCoordinator(
        #     hass, entry, "bms_extra", self.client, send.get_bms_extra(), receive.bms_extra)
        # self.dc_in_mode = DataPushCoordinator(
        #     hass, entry, "dc_in_mode", self.client, send.get_dc_in_mode(self.product), receive.dc_in_mode, None)
        # self.fan_auto = DataPushCoordinator(
        #     hass, entry, "fan_auto", self.client, send.get_fan_auto(), receive.fan_auto, None)
        # self.coordinators: dict[tuple, DataPushCoordinator] = {
        #     command.pd: self.pd,
        #     command.bms_main: self.bms_main,
        #     command.inv: self.inv,
        #     command.dc_in_mode(self.product): self.dc_in_mode,
        #     command.fan_auto: self.fan_auto,
        # }

        # self.client.connected_handler = self.__connected
        # self.client.disconnected_handler = self.__disconnected
        # self.client.received_handler = self.__received
        # self.client.run()

        def pd_updated(data: dict[str, Any]):
            self.diagnostics["pd"] = data
            if "pd_version" in data:
                self.device_info_main["sw_version"] = data["pd_version"]
                dr.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    **self.device_info_main,
                )
            # if self.__extra_connected != ef.has_extra(self.product, data.get("model", None)):
            #     self.__extra_connected = not self.__extra_connected
            #     if self.__extra_connected:
            #         self.__connected_extra()
            #     else:
            #         self.__disconnected_extra()
        self.pd.subscribe(pd_updated)

        # def extra_updated(data: dict[str, Any]):
        #     self.diagnostics["extra"] = data
        #     if self.device_info_extra is None:
        #         return
        #     if "battery_extra_version" in data:
        #         self.device_info_extra["sw_version"] = data["battery_extra_version"]
        #         dr.async_get_or_create(
        #             config_entry_id=entry.entry_id,
        #             **self.device_info_extra,
        #         )
        # self.extra.subscribe(extra_updated)

        def ems_updated(data: dict[str, Any]):
            self.diagnostics["ems"] = data
        self.ems.subscribe(ems_updated)

        def inverter_updated(data: dict[str, Any]):
            self.diagnostics["inverter"] = data
        self.inverter.subscribe(inverter_updated)

        def mppt_updated(data: dict[str, Any]):
            self.diagnostics["mppt"] = data
        self.mppt.subscribe(mppt_updated)

    async def close(self):
        self.tcp.close()
        await self.tcp.wait_closed()

    # def __connected_extra(self):
    #     async def f():
    #         try:
    #             data = receive.sn(await self.request(send.get_serial_extra()))
    #             self.serial_extra = data["serial"]
    #             model = self.device_info_main["model"]
    #             if model:
    #                 model += " Extra Battery"
    #             else:
    #                 model = "Extra Battery"
    #             self.device_info_extra = DeviceInfo(
    #                 identifiers={(DOMAIN, self.serial_extra)},
    #                 manufacturer="EcoFlow",
    #                 model=model,
    #                 name=f"{model} {self.serial_extra[-6:]}",
    #                 via_device=(DOMAIN, self.serial),
    #             )
    #             await self.bms_extra.async_refresh()
    #         except:
    #             self.__extra_connected = False
    #     create_task(f())

    def __disconnected_extra(self):
        self.serial_extra = None
        self.device_info_extra = None
        self.extra_disconnected.on_next(None)


class EcoFlowBaseEntity(Entity):
    def __init__(self, client: HassioEcoFlowClient, extra: bool):
        self._attr_available = False
        self._client = client
        self._is_extra = extra
        if extra:
            self.__serial = client.serial_extra
            self._attr_device_info = client.device_info_extra
            self._attr_name = client.device_info_extra["name"]
            self._attr_unique_id = client.serial_extra
        else:
            self.__serial = client.serial
            self._attr_device_info = client.device_info_main
            self._attr_name = client.device_info_main["name"]
            self._attr_unique_id = client.serial

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._is_extra:
            self._subscribe(self._client.extra_disconnected,
                            self.__on_disconnected)
        else:
            self._subscribe(self._client.disconnected, self.__on_disconnected)

    def _set_available(self):
        if not self._is_extra or self.__serial == self._client.serial_extra:
            self._attr_available = True

    def _subscribe(self, src: Observable, func: Callable):
        self.async_on_remove(src.subscribe(func).dispose)

    def __on_disconnected(self, *args):
        if self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()


class EcoFlowEntity(EcoFlowBaseEntity):
    def __init__(self, client: HassioEcoFlowClient, src: Observable[dict[str, Any]], key: str, name: str):
        super().__init__(client, False)
        self._key = key
        self._src = src
        self._attr_name += " " + name
        self._attr_unique_id += f"-{key.replace('_', '-')}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._src, self.__updated)

    def __updated(self, data: dict[str, Any]):
        self._set_available()
        self._on_updated(data)
        self.async_write_ha_state()

    def _on_updated(self, data: dict[str, Any]):
        pass


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
