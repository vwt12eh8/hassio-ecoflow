from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, EcoFlowDevice, EcoFlowEntity, select_bms
from .ecoflow import is_delta, is_power_station, is_river, is_river_mini, send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    device: EcoFlowDevice = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(device.product):
        entities.extend([
            AcEntity(device, device.inverter, "ac_out_state", "AC output"),
            BeepEntity(device, device.pd, "beep", "Beep"),
        ])
        if is_delta(device.product):
            entities.extend([
                AcPauseEntity(device, device.inverter,
                              "ac_in_pause", "AC charge"),
                DcEntity(device, device.mppt, "car_out_state", "DC output"),
                LcdAutoEntity(device, device.pd, "lcd_brightness",
                              "Screen brightness auto"),
            ])
        if is_river(device.product):
            entities.extend([
                AcSlowChargeEntity(device, device.inverter,
                                   "ac_in_slow", "AC slow charging"),
                DcEntity(device, device.pd, "car_out_state", "DC output"),
                FanAutoEntity(device, device.inverter,
                              "fan_config", "Auto fan speed"),
            ])
            if device.product == 5:  # RIVER Max
                entities.extend([
                    AmbientSyncEntity(device, device.bms.pipe(
                        select_bms(1)), "ambient_mode", "Ambient light sync screen", 1)
                ])
        if not is_river_mini(device.product):
            entities.extend([
                XBoostEntity(device, device.inverter,
                             "ac_out_xboost", "AC X-Boost"),
            ])

    async_add_entities(entities)


class SimpleEntity(SwitchEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = bool(data[self._key])


class AcEntity(SimpleEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_ac_out(self._device.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_ac_out(self._device.product, True))


class AcPauseEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = not bool(data[self._key])

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_ac_in_limit(pause=True))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_ac_in_limit(pause=False))


class AcSlowChargeEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:car-speed-limiter"

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_ac_in_slow(False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_ac_in_slow(True))


class AmbientSyncEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:sync-off" if self.is_on is False else "mdi:sync"

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_ambient(2))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_ambient(1))

    def _on_updated(self, data: dict[str, Any]):
        if data[self._key] == 1:
            self._attr_is_on = True
        elif data[self._key] == 2:
            self._attr_is_on = False
        else:
            self._attr_is_on = None


class BeepEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:volume-source" if self.is_on else "mdi:volume-mute"

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = not bool(data[self._key])

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_beep(False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_beep(True))


class DcEntity(SimpleEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_dc_out(self._device.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_dc_out(self._device.product, True))


class FanAutoEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:fan-auto" if self.is_on else "mdi:fan-chevron-up"

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_fan_auto(self._device.product, False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_fan_auto(self._device.product, True))

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
        self._device.send(send.set_lcd(self._device.product, light=value))

    async def async_turn_on(self, **kwargs: Any):
        value = self._brightness | 0x80
        self._device.send(send.set_lcd(self._device.product, light=value))


class XBoostEntity(SimpleEntity):
    _attr_entity_category = EntityCategory.CONFIG

    async def async_turn_off(self, **kwargs: Any):
        self._device.send(send.set_ac_out(
            self._device.product, xboost=False))

    async def async_turn_on(self, **kwargs: Any):
        self._device.send(send.set_ac_out(
            self._device.product, xboost=True))
