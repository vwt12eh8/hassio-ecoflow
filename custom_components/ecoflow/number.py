from typing import Any, Callable

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, POWER_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow import is_delta, send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_delta(client.product):
        entities.extend([
            ChargeWattsEntity(client, client.inverter,
                              "ac_in_limit_custom", "AC custom charge power"),
            LcdBrightnessEntity(client, client.pd,
                                "lcd_brightness", "LCD brightness"),
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
