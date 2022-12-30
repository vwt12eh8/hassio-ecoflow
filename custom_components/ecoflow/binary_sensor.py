from typing import Any

from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (DOMAIN, EcoFlowBaseEntity, EcoFlowData, EcoFlowDevice,
               EcoFlowEntity, EcoFlowExtraDevice, EcoFlowMainDevice)
from .ecoflow import is_delta, is_river, is_river_mini


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data: EcoFlowData = hass.data[DOMAIN]

    def device_added(device: EcoFlowDevice):
        entities = []
        if type(device) is EcoFlowMainDevice:
            entities.extend([
                ChargingEntity(device),
                MainErrorEntity(device),
            ])
            if is_delta(device.product):
                entities.extend([
                    InputEntity(device, device.inverter,
                                "ac_in_type", "AC input"),
                    InputEntity(device, device.mppt,
                                "dc_in_state", "DC input"),
                    CustomChargeEntity(device, device.inverter,
                                       "ac_in_limit_switch", "AC custom charge speed"),
                ])
            elif is_river(device.product):
                entities.extend([
                    InputEntity(device, device.inverter, "in_type", "Input"),
                ])
            elif is_river_mini(device.product):
                entities.extend([
                    InputEntity(device, device.inverter, "in_type", "Input"),
                ])
        elif type(device) is EcoFlowExtraDevice:
            entities.extend([
                ExtraErrorEntity(device, device.bms,
                                 "battery_error", "Status"),
            ])
        async_add_entities(entities)

    entry.async_on_unload(data.device_added.subscribe(device_added).dispose)
    for device in data.devices.values():
        device_added(device)


class BaseEntity(BinarySensorEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = bool(data[self._key])


class ChargingEntity(BinarySensorEntity, EcoFlowBaseEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _battery_level = None
    _battery_level_max = None
    _in_power = None
    _out_power = None

    def __init__(self, device: EcoFlowMainDevice):
        super().__init__(device)
        self._attr_name = "Charging"
        self._attr_unique_id += "-in-charging"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._device.pd, self.__updated)
        self._subscribe(self._device.ems, self.__updated)

    def __updated(self, data: dict[str, Any]):
        self._attr_available = True
        self._on_updated(data)
        self.async_write_ha_state()

    def _on_updated(self, data: dict[str, Any]):
        if "in_power" in data:
            self._in_power = data["in_power"]
        if "out_power" in data:
            self._out_power = data["out_power"]
        if "battery_level" in data:
            self._battery_level = data["battery_level"]
        if "battery_level_max" in data:
            self._battery_level_max = data["battery_level_max"]

        if not self._in_power:
            self._attr_is_on = False
        elif (self._battery_level is not None) and (self._battery_level_max is not None) and (self._battery_level_max < self._battery_level):
            self._attr_is_on = False
        elif (self._in_power is not None) and (self._out_power is not None) and (self._in_power <= self._out_power):
            self._attr_is_on = False
        else:
            self._attr_is_on = True


class CustomChargeEntity(BaseEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = data[self._key] == 2


class ExtraErrorEntity(BaseEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = data[self._key] not in [0, 6]
        self._attr_extra_state_attributes = {"code": data[self._key]}


class MainErrorEntity(BinarySensorEntity, EcoFlowBaseEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device: EcoFlowMainDevice):
        super().__init__(device)
        self._attr_name = "Status"
        self._attr_unique_id += "-error"
        self._attr_extra_state_attributes = {}

    @property
    def is_on(self):
        return next((True for x in self._attr_extra_state_attributes.values() if x not in [0, 6]), False)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._device.pd, self.__updated)
        self._subscribe(self._device.ems, self.__updated)
        self._subscribe(self._device.inverter, self.__updated)
        self._subscribe(self._device.mppt, self.__updated)

    def __updated(self, data: dict[str, Any]):
        self._attr_available = True
        if "ac_error" in data:
            self._attr_extra_state_attributes["ac"] = data["ac_error"]
        if "battery_main_error" in data:
            self._attr_extra_state_attributes["battery"] = data["battery_main_error"]
        if "dc_in_error" in data:
            self._attr_extra_state_attributes["dc"] = data["dc_in_error"]
        if "pd_error" in data:
            self._attr_extra_state_attributes["system"] = data["pd_error"]
        self.async_write_ha_state()


class InputEntity(BaseEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER
