from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ELECTRIC_CURRENT_AMPERE, PERCENTAGE, POWER_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, EcoFlowConfigEntity, EcoFlowDevice, EcoFlowEntity
from .ecoflow import (is_delta, is_delta_max, is_delta_mini, is_delta_pro,
                      is_power_station, send)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    device: EcoFlowDevice = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(device.product):
        entities.extend([
            DcInCurrentEntity(device, "dc_in_current_config",
                              "Car input"),
            MaxLevelEntity(device, device.ems,
                           "battery_level_max", "Charge level"),
        ])
        if is_delta(device.product):
            entities.extend([
                ChargeWattsEntity(device, device.inverter,
                                  "ac_in_limit_custom", "AC charge speed"),
                LcdBrightnessEntity(device, device.pd,
                                    "lcd_brightness", "Screen brightness"),
                MinLevelEntity(device, device.ems,
                            "battery_level_min", "Discharge level"),
            ])
            if is_delta_pro(device.product):
                entities.extend([
                    GenerateStartEntity(
                        device, device.ems, "generator_level_start", "Smart generator auto on"),
                    GenerateStopEntity(
                        device, device.ems, "generator_level_stop", "Smart generator auto off"),
                ])

    async_add_entities(entities)


class BaseEntity(NumberEntity, EcoFlowEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def _on_updated(self, data: dict[str, Any]):
        self._attr_native_value = data[self._key]


class ChargeWattsEntity(BaseEntity):
    _attr_icon = "mdi:car-speed-limiter"
    _attr_native_max_value = 1500
    _attr_native_min_value = 200
    _attr_native_step = 100
    _attr_native_unit_of_measurement = POWER_WATT

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_ac_in_limit(int(value)))

    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        voltage: float = data["ac_out_voltage_config"]
        if is_delta_max(self._device.product):
            if self._device.serial.startswith("DD"):
                self._attr_native_max_value = 1600
            elif voltage >= 220:
                self._attr_native_max_value = 2000
            elif voltage >= 120:
                self._attr_native_max_value = 1800
            elif voltage >= 110:
                self._attr_native_max_value = 1650
            else:
                self._attr_native_max_value = 1500
        elif is_delta_pro(self._device.product):
            if voltage >= 240:
                self._attr_native_max_value = 3000
            elif voltage >= 230:
                self._attr_native_max_value = 2900
            elif voltage >= 220:
                self._attr_native_max_value = 2200
            elif voltage >= 120:
                self._attr_native_max_value = 1800
            elif voltage >= 110:
                self._attr_native_max_value = 1650
            else:
                self._attr_native_max_value = 1500
        elif is_delta_mini(self._device.product):
            self._attr_native_max_value = 900
        else:
            self._attr_native_max_value = 1500


class DcInCurrentEntity(NumberEntity, EcoFlowConfigEntity):
    _attr_icon = "mdi:car-speed-limiter"
    _attr_native_max_value = 8
    _attr_native_min_value = 4
    _attr_native_step = 2
    _attr_native_unit_of_measurement = ELECTRIC_CURRENT_AMPERE

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_dc_in_current(
            self._device.product, int(value * 1000)))

    async def async_update(self):
        try:
            value = await self._device.request(send.get_dc_in_current(self._device.product), self._device.dc_in_current_config)
        except:
            return
        self._device.diagnostics["dc_in_current_config"] = value
        self._attr_native_value = int(value / 1000)
        self._attr_available = True


class GenerateStartEntity(BaseEntity):
    _attr_icon = "mdi:engine-outline"
    _attr_native_max_value = 30
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_generate_start(int(value)))


class GenerateStopEntity(BaseEntity):
    _attr_icon = "mdi:engine-off-outline"
    _attr_native_max_value = 100
    _attr_native_min_value = 50
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_generate_stop(int(value)))


class LcdBrightnessEntity(BaseEntity):
    _attr_icon = "mdi:brightness-6"
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def _on_updated(self, data: dict[str, Any]):
        self._attr_native_value = data[self._key] & 0x7F

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_lcd(
            self._device.product, light=int(value)))


class MaxLevelEntity(BaseEntity):
    _attr_icon = "mdi:battery-arrow-up"
    _attr_native_max_value = 100
    _attr_native_min_value = 30
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_level_max(
            self._device.product, int(value)))


class MinLevelEntity(BaseEntity):
    _attr_icon = "mdi:battery-arrow-down-outline"
    _attr_native_max_value = 30
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    async def async_set_native_value(self, value: float):
        self._device.send(send.set_level_min(int(value)))
