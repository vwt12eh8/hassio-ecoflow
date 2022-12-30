from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import FREQUENCY_HERTZ
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (DOMAIN, EcoFlowConfigEntity, EcoFlowData, EcoFlowDevice,
               EcoFlowEntity, EcoFlowMainDevice)
from .ecoflow import is_delta, is_river, is_river_mini, send

_AC_OPTIONS = {
    "Never": 0,
    "30min": 30,
    "2hour": 120,
    "4hour": 240,
    "6hour": 360,
    "12hour": 720,
    "24hour": 1440,
}

_FREQS = {
    "50Hz": 1,
    "60Hz": 2,
}

_DC_IMPUTS = {
    "Auto": 0,
    "Solar": 1,
    "Car": 2,
}

_DC_ICONS = {
    "Auto": None,
    "MPPT": "mdi:solar-power",
    "DC": "mdi:current-dc",
}

_LCD_OPTIONS = {
    "Never": 0,
    "10sec": 10,
    "30sec": 30,
    "1min": 60,
    "5min": 300,
    "30min": 1800,
}

_STANDBY_OPTIONS = {
    "Never": 0,
    "30min": 30,
    "1hour": 60,
    "2hour": 120,
    "6hour": 360,
    "12hour": 720,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data: EcoFlowData = hass.data[DOMAIN]

    def device_added(device: EcoFlowDevice):
        if type(device) is not EcoFlowMainDevice:
            return
        entities = [
            AcTimeoutEntity(device, device.inverter,
                            "ac_out_timeout", "AC timeout"),
            FreqEntity(device, device.inverter,
                       "ac_out_freq_config", "AC frequency"),
            StandbyTimeoutEntity(
                device, device.pd, "standby_timeout", "Unit timeout"),
        ]
        if is_delta(device.product):
            entities.extend([
                LcdTimeoutPushEntity(device, device.pd,
                                     "lcd_timeout", "Screen timeout"),
            ])
        if is_river(device.product):
            entities.extend([
                DcInTypeEntity(device),
                LcdTimeoutPollEntity(device, "lcd_timeout", "Screen timeout"),
            ])
        if is_river_mini(device.product):
            entities.extend([
                LcdTimeoutPushEntity(device, device.pd,
                                     "lcd_timeout", "Screen timeout"),
            ])
        async_add_entities(entities)

    entry.async_on_unload(data.device_added.subscribe(device_added).dispose)
    for device in data.devices.values():
        device_added(device)


class AcTimeoutEntity(SelectEntity, EcoFlowEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-settings"
    _attr_options = list(_AC_OPTIONS.keys())

    async def async_select_option(self, option: str):
        self._device.send(send.set_ac_timeout(_AC_OPTIONS[option]))

    def _on_updated(self, data: dict[str, Any]):
        value = data[self._key]
        self._attr_current_option = next(
            (i for i in _AC_OPTIONS if _AC_OPTIONS[i] == value), None)


class DcInTypeEntity(SelectEntity, EcoFlowConfigEntity):
    _attr_current_option = None
    _attr_options = list(_DC_IMPUTS.keys())

    def __init__(self, device: EcoFlowMainDevice):
        super().__init__(device, "dc_in_type_config", "DC mode")
        self._req = send.get_dc_in_type(device.product)

    @property
    def icon(self):
        return _DC_ICONS.get(self.current_option, None)

    async def async_select_option(self, option: str):
        self._device.send(send.set_dc_in_type(
            self._device.product, _DC_IMPUTS[option]))

    async def async_update(self):
        try:
            value = await self._device.request(self._req, self._device.dc_in_type)
        except:
            return
        self._device.diagnostics["dc_in_type"] = value
        self._attr_current_option = next(
            (i for i in _DC_IMPUTS if _DC_IMPUTS[i] == value), None)
        self._attr_available = True


class FreqEntity(SelectEntity, EcoFlowEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:sine-wave"
    _attr_options = list(_FREQS.keys())
    _attr_unit_of_measurement = FREQUENCY_HERTZ

    async def async_select_option(self, option: str):
        self._device.send(send.set_ac_out(
            self._device.product, freq=_FREQS[option]))

    def _on_updated(self, data: dict[str, Any]):
        value = data[self._key]
        self._attr_current_option = next(
            (i for i in _FREQS if _FREQS[i] == value), None)


class LcdTimeoutPollEntity(SelectEntity, EcoFlowConfigEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-settings"
    _attr_options = list(_LCD_OPTIONS.keys())
    _req = send.get_lcd()

    async def async_select_option(self, option: str):
        self._device.send(send.set_lcd(
            self._device.product, time=_LCD_OPTIONS[option]))

    async def async_update(self):
        try:
            value = await self._device.request(self._req, self._device.lcd_timeout)
        except:
            return
        self._device.diagnostics["lcd_timeout"] = value
        self._attr_current_option = next(
            (i for i in _LCD_OPTIONS if _LCD_OPTIONS[i] == value), None)
        self._attr_available = True


class LcdTimeoutPushEntity(SelectEntity, EcoFlowEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-settings"
    _attr_options = list(_LCD_OPTIONS.keys())

    async def async_select_option(self, option: str):
        self._device.send(send.set_lcd(
            self._device.product, time=_LCD_OPTIONS[option]))

    def _on_updated(self, data: dict[str, Any]):
        value = data[self._key]
        self._attr_current_option = next(
            (i for i in _LCD_OPTIONS if _LCD_OPTIONS[i] == value), None)


class StandbyTimeoutEntity(SelectEntity, EcoFlowEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-settings"
    _attr_options = list(_STANDBY_OPTIONS.keys())

    async def async_select_option(self, option: str):
        self._device.send(
            send.set_standby_timeout(_STANDBY_OPTIONS[option]))

    def _on_updated(self, data: dict[str, Any]):
        value = data[self._key]
        self._attr_current_option = next(
            (i for i in _STANDBY_OPTIONS if _STANDBY_OPTIONS[i] == value), None)
