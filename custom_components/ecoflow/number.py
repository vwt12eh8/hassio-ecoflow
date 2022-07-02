from typing import Any, Callable

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ELECTRIC_CURRENT_AMPERE, PERCENTAGE, POWER_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import (DOMAIN, EcoFlowConfigEntity, EcoFlowEntity, HassioEcoFlowClient,
               request)
from .ecoflow import is_delta, is_delta_pro, is_power_station, send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(client.product):
        entities.extend([
            DcInCurrentEntity(client, "dc_in_current_config",
                              "Car input current"),
            MaxLevelEntity(client, client.ems,
                           "battery_level_max", "Battery max"),
        ])
        if is_delta(client.product):
            entities.extend([
                ChargeWattsEntity(client, client.inverter,
                                  "ac_in_limit_custom", "AC custom charge power"),
                LcdBrightnessEntity(client, client.pd,
                                    "lcd_brightness", "LCD brightness"),
                MinLevelEntity(client, client.ems,
                            "battery_level_min", "Battery min"),
            ])
            if is_delta_pro(client.product):
                entities.extend([
                    GenerateStartEntity(
                        client, client.ems, "generator_level_start", "Generator start"),
                    GenerateStopEntity(
                        client, client.ems, "generator_level_stop", "Generator stop"),
                ])

    async_add_entities(entities)


class BaseEntity(NumberEntity, EcoFlowEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def _on_updated(self, data: dict[str, Any]):
        self._attr_value = data[self._key]


class ChargeWattsEntity(BaseEntity):
    _attr_icon = "mdi:car-speed-limiter"
    _attr_max_value = 1500
    _attr_min_value = 200
    _attr_step = 100
    _attr_unit_of_measurement = POWER_WATT

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_ac_in_limit(int(value)))

    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        self._attr_extra_state_attributes = {
            "custom_enable": (data["ac_in_limit_switch"] == 2),
        }


class DcInCurrentEntity(NumberEntity, EcoFlowConfigEntity):
    _attr_icon = "mdi:car-speed-limiter"
    _attr_max_value = 8
    _attr_min_value = 4
    _attr_step = 2
    _attr_unit_of_measurement = ELECTRIC_CURRENT_AMPERE

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_dc_in_current(
            self._client.product, int(value * 1000)))

    async def async_update(self):
        value = await request(self._client.tcp, send.get_dc_in_current(self._client.product), self._client.dc_in_current_config)
        self._client.diagnostics["dc_in_current_config"] = value
        self._attr_value = int(value / 1000)
        self._attr_available = True


class GenerateStartEntity(BaseEntity):
    _attr_icon = "mdi:engine-outline"
    _attr_max_value = 30
    _attr_min_value = 0
    _attr_step = 1
    _attr_unit_of_measurement = PERCENTAGE

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_generate_start(int(value)))


class GenerateStopEntity(BaseEntity):
    _attr_icon = "mdi:engine-off-outline"
    _attr_max_value = 100
    _attr_min_value = 50
    _attr_step = 1
    _attr_unit_of_measurement = PERCENTAGE

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_generate_stop(int(value)))


class LcdBrightnessEntity(BaseEntity):
    _attr_icon = "mdi:brightness-6"
    _attr_max_value = 100
    _attr_min_value = 0
    _attr_step = 1
    _attr_unit_of_measurement = PERCENTAGE

    def _on_updated(self, data: dict[str, Any]):
        self._attr_value = data[self._key] & 0x7F

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_lcd(
            self._client.product, light=int(value)))


class MaxLevelEntity(BaseEntity):
    _attr_icon = "mdi:battery-arrow-up"
    _attr_max_value = 100
    _attr_min_value = 30
    _attr_step = 1
    _attr_unit_of_measurement = PERCENTAGE

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_level_max(
            self._client.product, int(value)))


class MinLevelEntity(BaseEntity):
    _attr_icon = "mdi:battery-arrow-down-outline"
    _attr_max_value = 30
    _attr_min_value = 0
    _attr_step = 1
    _attr_unit_of_measurement = PERCENTAGE

    async def async_set_value(self, value: float):
        self._client.tcp.write(send.set_level_min(int(value)))
