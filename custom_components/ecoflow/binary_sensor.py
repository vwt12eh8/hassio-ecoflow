from typing import Any, Callable

import reactivex.operators as ops
from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import (DOMAIN, EcoFlowBaseEntity, EcoFlowEntity, HassioEcoFlowClient,
               select_bms)
from .ecoflow import is_delta, is_power_station, is_river


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(client.product):
        entities.extend([
            ChargingEntity(client),
            MainErrorEntity(client),
        ])
        if is_delta(client.product):
            entities.extend([
                ExtraErrorEntity(client, client.bms.pipe(select_bms(
                    1), ops.share()), "battery_error", "Extra1 status", 1),
                ExtraErrorEntity(client, client.bms.pipe(select_bms(
                    2), ops.share()), "battery_error", "Extra2 status", 2),
                InputEntity(client, client.inverter, "ac_in_type", "AC input"),
                InputEntity(client, client.mppt, "dc_in_state", "DC input"),
                CustomChargeEntity(client, client.inverter,
                                   "ac_in_limit_switch", "AC custom charge"),
            ])
        if is_river(client.product):
            entities.extend([
                ExtraErrorEntity(client, client.bms.pipe(select_bms(
                    1), ops.share()), "battery_error", "Extra status", 1),
                InputEntity(client, client.inverter, "in_type", "Input"),
            ])

    async_add_entities(entities)


class BaseEntity(BinarySensorEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_is_on = bool(data[self._key])


class ChargingEntity(BinarySensorEntity, EcoFlowBaseEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _battery_level = None
    _battery_level_max = None
    _in_power = None
    _out_power = None

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client)
        self._attr_name += " Charging"
        self._attr_unique_id += "-in-charging"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.pd, self.__updated)
        self._subscribe(self._client.ems, self.__updated)

    def __updated(self, data: dict[str, Any]):
        self._attr_available = True
        self._on_updated(data)
        self.async_write_ha_state()

    def _on_updated(self, data: dict[str, Any]):
        if "in_power" in data:
            self._in_power = bool(data["in_power"])
        if "out_power" in data:
            self._out_power = bool(data["out_power"])
        if "battery_level" in data:
            self._battery_level = data["battery_level"]
        if "battery_level_max" in data:
            self._battery_level_max = data["battery_level_max"]

        if not self._in_power:
            self._attr_is_on = False
        elif self._battery_level is not None and self._battery_level_max is not None and self._battery_level_max < self._battery_level:
            self._attr_is_on = False
        elif self._in_power is not None and self._out_power is not None and self._in_power < self._out_power:
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
        super()._on_updated(data)
        self._attr_extra_state_attributes = {"code": data[self._key]}


class MainErrorEntity(BinarySensorEntity, EcoFlowBaseEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client)
        self._attr_name += " Main status"
        self._attr_unique_id += "-error"
        self._attr_extra_state_attributes = {}

    @property
    def is_on(self):
        return next((True for x in self._attr_extra_state_attributes.values() if x != 0), False)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.pd, self.__updated)
        self._subscribe(self._client.ems, self.__updated)
        self._subscribe(self._client.inverter, self.__updated)
        self._subscribe(self._client.mppt, self.__updated)

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
