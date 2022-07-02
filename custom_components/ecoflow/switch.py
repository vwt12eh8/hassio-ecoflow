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
            BeepEntity(client, client.pd, "beep", "Beep"),
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
                AcSlowChargeEntity(client, client.inverter,
                                   "ac_in_slow", "AC slow charge"),
                DcEntity(client, client.pd, "car_out_state", "DC output"),
                FanAutoEntity(client, client.inverter,
                              "fan_config", "Fan auto"),
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


class AcSlowChargeEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:car-speed-limiter"

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_in_slow(False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_ac_in_slow(True))


class BeepEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:volume-source" if self.is_on else "mdi:volume-mute"

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = not bool(data[self._key])

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_beep(False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_beep(True))


class DcEntity(SimpleEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_dc_out(self._client.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_dc_out(self._client.product, True))


class FanAutoEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:fan-auto" if self.is_on else "mdi:fan-chevron-up"

    async def async_turn_off(self, **kwargs: Any):
        self._client.tcp.write(send.set_fan_auto(self._client.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._client.tcp.write(send.set_fan_auto(self._client.product, True))

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = data[self._key] == 1


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
