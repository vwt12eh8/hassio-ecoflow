from typing import Any, Callable

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow import is_delta, is_power_station, is_river, is_river_mini, send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(client.product):
        entities.extend([
            AcEntity(client, client.inverter, "ac_out_state", "AC output"),
        ])
        if is_delta(client.product):
            entities.extend([
                AcPauseEntity(client, client.inverter,
                              "ac_in_pause", "AC charge"),
                DcEntity(client, client.mppt, "car_out_state", "DC output"),
                LcdAutoEntity(client, client.pd, "lcd_brightness",
                              "LCD brightness auto"),
            ])
        if is_river(client.product):
            entities.extend([
                DcEntity(client, client.pd, "car_out_state", "DC output"),
            ])
        if not is_river_mini(client.product):
            entities.extend([
                XBoostEntity(client, client.inverter,
                             "ac_out_xboost", "AC X-Boost"),
            ])

    async_add_entities(entities)


class SimpleEntity(SwitchEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = bool(data[self._key])


class AcEntity(SimpleEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_out(self._client.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_out(self._client.product, True))


class AcPauseEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = not bool(data[self._key])

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_in_limit(pause=True))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_in_limit(pause=False))


class DcEntity(SimpleEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_dc_out(self._client.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_dc_out(self._client.product, True))


class LcdAutoEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:brightness-auto"
    _brightness = 0

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = bool(data[self._key] & 0x80)
        self._brightness = data[self._key] & 0x7F

    async def async_turn_off(self, **kwargs: Any):
        value = self._brightness
        self._client.tcp.write(send.set_lcd(self._client.product, light=value))

    async def async_turn_on(self, **kwargs: Any):
        value = self._brightness | 0x80
        self._client.tcp.write(send.set_lcd(self._client.product, light=value))


class XBoostEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_out(
            self._client.product, xboost=False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_out(
            self._client.product, xboost=True))
