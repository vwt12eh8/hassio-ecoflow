from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar, cast

import reactivex.operators as ops
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.device_registry import async_get as async_get_dr
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.util.dt import utcnow
from reactivex import Observable, Subject, compose, throw
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
    Platform.SELECT,
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
    try:
        tcp.write(req)
    except BaseException as ex:
        t.close()
        raise ex
    return await t


def select_bms(idx: int):
    return compose(
        ops.filter(lambda x: x[0] == idx),
        ops.map(lambda x: cast(dict[str, Any], x[1])),
    )


class HassioEcoFlowClient:
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
        self.bms = self.received.pipe(
            ops.filter(receive.is_bms),
            ops.map(lambda x: receive.parse_bms(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )

        self.dc_in_current_config = self.received.pipe(
            ops.filter(receive.is_dc_in_current_config),
            ops.map(lambda x: receive.parse_dc_in_current_config(x[3])),
        )
        self.dc_in_type = self.received.pipe(
            ops.filter(receive.is_dc_in_type),
            ops.map(lambda x: receive.parse_dc_in_type(x[3])),
        )
        self.fan_auto = self.received.pipe(
            ops.filter(receive.is_fan_auto),
            ops.map(lambda x: receive.parse_fan_auto(x[3])),
        )
        self.lcd_timeout = self.received.pipe(
            ops.filter(receive.is_lcd_timeout),
            ops.map(lambda x: receive.parse_lcd_timeout(x[3])),
        )

        self.disconnected = Subject[Optional[int]]()

        def _disconnected(*args):
            self.__disconnected = None
            self.tcp.reconnect()
            self.diagnostics.clear()
            self.disconnected.on_next(None)
            if self.__extra_connected:
                self.__extra_connected = False

        def reset_timer(*args):
            if self.__disconnected:
                self.__disconnected()
            self.__disconnected = event.async_track_point_in_utc_time(
                hass,
                _disconnected,
                utcnow().replace(microsecond=0) + (DISCONNECT_TIME + timedelta(seconds=1)),
            )

        def end_timer(ex=None):
            self.disconnected.on_next(None)
            if ex:
                self.disconnected.on_error(ex)
            else:
                self.disconnected.on_completed()
        self.received.subscribe(reset_timer, end_timer, end_timer)

        def pd_updated(data: dict[str, Any]):
            self.diagnostics["pd"] = data
            self.device_info_main["model"] = ef.get_model_name(
                self.product, data["model"])
            dr.async_get_or_create(
                config_entry_id=entry.entry_id,
                **self.device_info_main,
            )
            if self.__extra_connected != ef.has_extra(self.product, data.get("model", None)):
                self.__extra_connected = not self.__extra_connected
                if not self.__extra_connected:
                    self.disconnected.on_next(1)
        self.pd.subscribe(pd_updated)

        def bms_updated(data: tuple[int, dict[str, Any]]):
            if "bms" not in self.diagnostics:
                self.diagnostics["bms"] = dict[str, Any]()
            self.diagnostics["bms"][data[0]] = data[1]
        self.bms.subscribe(bms_updated)

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


class EcoFlowBaseEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _connected = False

    def __init__(self, client: HassioEcoFlowClient, bms_id: Optional[int] = None):
        self._attr_available = False
        self._client = client
        self._bms_id = bms_id or 0
        self._attr_device_info = client.device_info_main
        self._attr_unique_id = client.serial
        if bms_id:
            self._attr_unique_id += f"-{bms_id}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.disconnected, self.__on_disconnected)

    def _subscribe(self, src: Observable, func: Callable):
        self.async_on_remove(src.subscribe(func).dispose)

    def __on_disconnected(self, bms_id: Optional[int]):
        if bms_id is not None and self._bms_id != bms_id:
            return
        self._connected = False
        if self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()


class EcoFlowEntity(EcoFlowBaseEntity):
    def __init__(self, client: HassioEcoFlowClient, src: Observable[dict[str, Any]], key: str, name: str, bms_id: Optional[int] = None):
        super().__init__(client, bms_id)
        self._key = key
        self._src = src
        self._attr_name = name
        self._attr_unique_id += f"-{key.replace('_', '-')}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._src, self.__updated)

    def __updated(self, data: dict[str, Any]):
        self._attr_available = True
        self._on_updated(data)
        self.async_write_ha_state()

    def _on_updated(self, data: dict[str, Any]):
        pass


class EcoFlowConfigEntity(EcoFlowBaseEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = True

    def __init__(self, client: HassioEcoFlowClient, key: str, name: str):
        super().__init__(client)
        self._attr_name = name
        self._attr_unique_id += f"-{key.replace('_', '-')}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.received, self.__updated)

    def __updated(self, data):
        if not self._connected:
            self._connected = True
            self.async_schedule_update_ha_state(True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    client = HassioEcoFlowClient(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    client: HassioEcoFlowClient = hass.data[DOMAIN].pop(entry.entry_id)
    await client.close()
    return True
