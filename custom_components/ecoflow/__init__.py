from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Semaphore
from datetime import timedelta
from typing import Any, Callable, TypeVar, cast

import reactivex.operators as ops
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import (CONNECTION_NETWORK_MAC,
                                                   DeviceEntry)
from homeassistant.helpers.device_registry import async_get as async_get_dr
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.util.dt import utcnow
from reactivex import Observable, Subject, compose, throw
from reactivex.subject.replaysubject import ReplaySubject

from . import ecoflow as ef
from .ecoflow import receive, send
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
        ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
        ops.ref_count(),
    )


class EcoFlowData:
    def __init__(self):
        self.device_added = Subject[EcoFlowDevice]()
        self.devices = dict[str, EcoFlowDevice]()


class EcoFlowDevice(ABC):
    bms: Observable[dict[str, Any]]
    device_info: DeviceInfo
    product: int
    serial: str

    def __init__(self):
        self.disconnected = Subject[int | None]()

    @abstractmethod
    async def request(self, req: bytes, res: Observable[_T]) -> _T:
        pass

    @abstractmethod
    def send(self, data: bytes):
        pass


class EcoFlowMainDevice(EcoFlowDevice):
    __disconnected = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, serial: str):
        super().__init__()
        data = entry.data[serial]
        self.data: EcoFlowData = hass.data[DOMAIN]
        self._tcp = RxTcpAutoConnection(data[CONF_HOST], ef.PORT)
        self.product: int = data[CONF_PRODUCT]
        self.serial = serial
        self.serial_extra = dict[int, str]()
        self.sem_extra = Semaphore(1)
        self.diagnostics = dict[str, dict[str, Any]]()
        self._dr = async_get_dr(hass)
        self.entry_id = entry.entry_id

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer="EcoFlow",
            name=f"{ef.get_model_name(self.product)} {serial[-6:]}",
        )
        if mac := data.get(CONF_MAC, None):
            self.device_info["connections"] = {
                (CONNECTION_NETWORK_MAC, mac),
            }

        self.received = self._tcp.received.pipe(
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
        self._bms = self.received.pipe(
            ops.filter(receive.is_bms),
            ops.map(lambda x: receive.parse_bms(x[3], self.product)),
            ops.multicast(subject=ReplaySubject(1, DISCONNECT_TIME)),
            ops.ref_count(),
        )
        self.bms = self._bms.pipe(select_bms(0))
        if ef.is_river(self.product):
            self._bms.pipe(
                ops.filter(lambda x: x[0] != 0),
            ).subscribe(lambda x: hass.create_task(self._bms_updated(*x)))

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

        def _disconnected(*args):
            self.__disconnected = None
            self._tcp.reconnect()
            self.diagnostics.clear()
            self._clear_extra()
            self.disconnected.on_next(None)

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
            self.device_info["model"] = ef.get_model_name(
                self.product, data["model"])
            self._dr.async_get_or_create(
                config_entry_id=entry.entry_id,
                **self.device_info,
            )
            if self.serial_extra and not ef.has_extra(self.product, data.get("model", None)):
                self._clear_extra()
                self.disconnected.on_next(1)  # deprecated
        self.pd.subscribe(pd_updated)

        def bms_updated(data: tuple[int, dict[str, Any]]):
            if "bms" not in self.diagnostics:
                self.diagnostics["bms"] = dict[str, Any]()
            self.diagnostics["bms"][data[0]] = data[1]
            if data[0] == 0:
                self._dr.async_get_or_create(
                    config_entry_id=self.entry_id,
                    identifiers={(DOMAIN, serial)},
                    sw_version=data[1]["battery_version"] + " (BMS)",
                )
        self._bms.subscribe(bms_updated)

        def ems_updated(data: dict[str, Any]):
            self.diagnostics["ems"] = data
            if "battery_main_version" in data:
                self._dr.async_get_or_create(
                    config_entry_id=self.entry_id,
                    identifiers={(DOMAIN, serial)},
                    sw_version=data["battery_main_version"] + " (BMS)",
                )
        self.ems.subscribe(ems_updated)

        def inverter_updated(data: dict[str, Any]):
            self.diagnostics["inverter"] = data
        self.inverter.subscribe(inverter_updated)

        def mppt_updated(data: dict[str, Any]):
            self.diagnostics["mppt"] = data
        self.mppt.subscribe(mppt_updated)

    async def close(self):
        self._tcp.close()
        await self._tcp.wait_closed()

    async def request(self, req: bytes, res: Observable[_T]):
        return await request(self._tcp, req, res)

    def send(self, data: bytes):
        self._tcp.write(data)

    async def _bms_updated(self, idx: int, data: dict[str, Any]):
        if idx not in self.serial_extra:
            async with self.sem_extra:
                if idx not in self.serial_extra:
                    serial = await self.request(
                        send.get_serial_extra(),
                        self.received.pipe(
                            ops.filter(receive.is_serial_extra),
                            ops.map(lambda x: receive.parse_serial(x[3])),
                        ),
                    )
                    serial = serial["serial"]
                    self.serial_extra[idx] = serial
                    if serial not in self.data.devices:
                        device = EcoFlowExtraDevice(serial, self.product)
                        self.data.devices[serial] = device
                        device.parent = self
                        self.data.device_added.on_next(device)
                    else:
                        device: EcoFlowExtraDevice = self.data.devices[serial]
                        device.parent = self
                    self._dr.async_get_or_create(
                        config_entry_id=self.entry_id,
                        identifiers={(DOMAIN, serial)},
                        sw_version=data["battery_version"],
                        via_device=device.device_info["via_device"],
                    )
        self.data.devices[self.serial_extra[idx]].bms.on_next(data)

    def _clear_extra(self):
        serials = list(self.serial_extra.values())
        self.serial_extra.clear()
        for serial in serials:
            device: EcoFlowExtraDevice = self.data.devices[serial]
            device.parent = None
            device.disconnected.on_next(None)


class EcoFlowExtraDevice(EcoFlowDevice):
    parent: EcoFlowMainDevice | None = None

    def __init__(self, serial: str, product: int):
        super().__init__()
        self.bms = Subject()
        self.product = product
        self.serial = serial

    @property
    def device_info(self):
        parent = self.parent.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer=parent["manufacturer"],
            model=parent["model"] + " Extra Battery",
            name=f"{ef.get_model_name(self.product)} Extra {self.serial[-6:]}",
            via_device=(DOMAIN, self.parent.serial),
        )

    async def request(self, req: bytes, res: Observable[_T]):
        return self.parent.request(req, res)

    def send(self, data: bytes):
        return self.parent.send(data)


class EcoFlowBaseEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _connected = False

    def __init__(self, device: EcoFlowDevice, bms_id: int | None = None):
        self._attr_available = False
        self._device = device
        self._bms_id = bms_id or 0
        self._attr_device_info = device.device_info
        self._attr_unique_id = device.serial
        if bms_id:
            self._attr_unique_id += f"-{bms_id}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._device.disconnected, self.__on_disconnected)

    def _subscribe(self, src: Observable, func: Callable):
        self.async_on_remove(src.subscribe(func).dispose)

    def __on_disconnected(self, bms_id: int | None):
        if bms_id is not None and self._bms_id != bms_id:
            return
        self._connected = False
        if self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()


class EcoFlowEntity(EcoFlowBaseEntity):
    def __init__(self, device: EcoFlowDevice, src: Observable[dict[str, Any]], key: str, name: str, bms_id: int | None = None):
        super().__init__(device, bms_id)
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

    def __init__(self, device: EcoFlowDevice, key: str, name: str):
        super().__init__(device)
        self._attr_name = name
        self._attr_unique_id += f"-{key.replace('_', '-')}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._device.received, self.__updated)

    def __updated(self, data):
        if not self._connected:
            self._connected = True
            self.async_schedule_update_ha_state(True)


async def _entry_updated(hass: HomeAssistant, entry: ConfigEntry):
    data: EcoFlowData = hass.data[DOMAIN]

    for serial in list(data.devices):
        if serial in entry.data:
            continue
        device = data.devices.pop(serial)
        entry.async_create_task(hass, device.close())

    for serial in entry.data:
        if serial in data.devices:
            continue
        device = EcoFlowMainDevice(hass, entry, serial)
        data.devices[serial] = device
        data.device_added.on_next(device)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.unique_id != DOMAIN:
        return False

    hass.data[DOMAIN] = EcoFlowData()
    hass.config_entries.async_setup_platforms(entry, _PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_entry_updated))
    entry.async_create_task(hass, _entry_updated(hass, entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    data: EcoFlowData = hass.data[DOMAIN]

    for device in data.devices.values():
        await device.close()

    hass.data.pop(DOMAIN)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.version == 1:
        de = next((x for x in hass.config_entries.async_entries(
            DOMAIN) if x.unique_id == DOMAIN), None)
        if de:
            data = dict(de.data)
            data[entry.unique_id] = dict(entry.data)
            title = de.title
        else:
            data = {entry.unique_id: dict(entry.data)}
            de = entry
            de.version = 2
            title = ""
        hass.config_entries.async_update_entry(
            de, data=data, title=title, unique_id=DOMAIN)
        if de != entry:
            await hass.config_entries.async_remove(entry.entry_id)
    return True


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry):
    serial = next((x[1] for x in device.identifiers if x[0] == DOMAIN), None)
    if not serial:
        return False
    if serial not in entry.data:
        return True

    data = dict(entry.data)
    data.pop(serial)
    hass.config_entries.async_update_entry(entry, data=data)
    return True
