from typing import Any, Callable, Optional

import reactivex.operators as ops
from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ELECTRIC_POTENTIAL_VOLT, ENERGY_WATT_HOUR,
                                 PERCENTAGE, POWER_WATT, TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from reactivex import Observable

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient, select_bms
from .ecoflow import is_delta, is_power_station, is_river


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(client.product):
        entities.extend([
            EnergyEntity(client, client.pd, "mppt_in_energy",
                         "MPPT input energy"),
            EnergySumEntity(client, "in_energy", [
                            "ac", "car", "mppt"], "Total input energy"),
            EnergySumEntity(client, "out_energy", [
                            "ac", "car"], "Total output energy"),
            FanEntity(client, client.inverter, "fan_state", "Fan"),
            TotalLevelEntity(client, client.pd, "battery_level",
                             "Battery"),
            WattsEntity(client, client.pd, "in_power", "Total input"),
            WattsEntity(client, client.pd, "out_power", "Total output"),
            WattsEntity(client, client.inverter, "ac_out_power", "AC output"),
            WattsEntity(client, client.pd, "usb_out1_power",
                        "USB-A left output"),
            WattsEntity(client, client.pd, "usb_out2_power",
                        "USB-A right output"),
        ])
        if is_delta(client.product):
            bms = (
                client.bms.pipe(select_bms(0), ops.share()),
                client.bms.pipe(select_bms(1), ops.share()),
                client.bms.pipe(select_bms(2), ops.share()),
            )
            entities.extend([
                SingleLevelEntity(
                    client, bms[0], "battery_level_f32", "Main battery"),
                SingleLevelEntity(
                    client, bms[1], "battery_level_f32", "Extra1 battery", 1),
                SingleLevelEntity(
                    client, bms[2], "battery_level_f32", "Extra2 battery", 2),
                TempEntity(client, bms[0], "battery_temp",
                           "Main battery temperature"),
                TempEntity(client, bms[1], "battery_temp",
                           "Extra1 battery temperature", 1),
                TempEntity(client, bms[2], "battery_temp",
                           "Extra2 battery temperature", 2),
                TempEntity(client, client.pd, "typec_out1_temp",
                           "USB-C left temperature"),
                TempEntity(client, client.pd, "typec_out2_temp",
                           "USB-C right temperature"),
                VoltageEntity(client, client.mppt, "dc_in_voltage",
                              "DC input voltage"),
                WattsEntity(client, client.inverter,
                            "ac_in_power", "AC input"),
                WattsEntity(client, client.mppt, "dc_in_power", "DC input"),
                WattsEntity(client, client.mppt, "car_out_power", "DC output"),
                WattsEntity(client, client.pd, "usbqc_out1_power",
                            "USB-FC left output"),
                WattsEntity(client, client.pd, "usbqc_out2_power",
                            "USB-FC right output"),
                WattsEntity(client, client.pd, "typec_out1_power",
                            "USB-C left output"),
                WattsEntity(client, client.pd, "typec_out2_power",
                            "USB-C right output"),
            ])
            if client.product == 14:  # DELTA Pro
                entities.append(WattsEntity(client, client.mppt,
                                "anderson_out_power", "Anderson output"))
        if is_river(client.product):
            extra = client.bms.pipe(select_bms(1), ops.share())
            entities.extend([
                SingleLevelEntity(client, client.ems, "battery_main_level",
                            "Main battery"),
                SingleLevelEntity(
                    client, extra, "battery_level", "Extra battery", 1),
                TempEntity(client, client.ems, "battery_main_temp",
                           "Main battery temperature"),
                TempEntity(client, extra, "battery_temp",
                           "Extra battery temperature", 1),
                TempEntity(client, client.pd, "car_out_temp",
                           "DC output temperature"),
                TempEntity(client, client.pd, "typec_out1_temp",
                           "USB-C temperature"),
                VoltageEntity(client, client.inverter, "dc_in_voltage",
                              "DC input voltage"),
                WattsEntity(client, client.pd, "car_out_power", "DC output"),
                WattsEntity(client, client.pd, "light_power", "Light output"),
                WattsEntity(client, client.pd, "usbqc_out1_power",
                            "USB-FC output"),
                WattsEntity(client, client.pd, "typec_out1_power",
                            "USB-C output"),
            ])

    async_add_entities(entities)


class BaseEntity(SensorEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_native_value = data[self._key]


class EnergyEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING


class EnergySumEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, client: HassioEcoFlowClient, key: str, keys: list[str], name: str):
        super().__init__(client, client.pd, key, name)
        self._suffix_len = len(key) + 1
        self._keys = [f"{x}_{key}" for x in keys]

    def _on_updated(self, data: dict[str, Any]):
        values = {key[:-self._suffix_len]: data[key]
                  for key in data if key in self._keys}
        self._attr_extra_state_attributes = values
        self._attr_native_value = sum(values.values())


class FanEntity(BaseEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def icon(self):
        value = self.native_value
        if value is None or self.native_value <= 0:
            return "mdi:fan-off"
        return "mdi:fan"


class LevelEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, src: Observable[dict[str, Any]], key: str, name: str, bms_id: Optional[int] = None):
        super().__init__(client, src, key, name, bms_id)
        self._attr_extra_state_attributes = {}


class SingleLevelEntity(LevelEntity):
    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        if "battery_main_capacity_remain" in data:
            self._attr_extra_state_attributes["capacity_remain"] = data["battery_main_capacity_remain"]
        if "battery_main_capacity_full" in data:
            self._attr_extra_state_attributes["capacity_full"] = data["battery_main_capacity_full"]
        if "battery_capacity_remain" in data:
            self._attr_extra_state_attributes["capacity_remain"] = data["battery_capacity_remain"]
        if "battery_capacity_full" in data:
            self._attr_extra_state_attributes["capacity_full"] = data["battery_capacity_full"]


class TempEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT


class TotalLevelEntity(LevelEntity):
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.ems, self.__ems_updated)

    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        self._attr_extra_state_attributes["remain_time"] = data["remain_display"].__str__(
        )

    def __ems_updated(self, data: dict[str, Any]):
        self._attr_extra_state_attributes.update({
            "limit_max": data["battery_level_max"],
        })
        if self._client.product == 14:
            self._attr_extra_state_attributes.update({
                "limit_min": data["battery_level_min"],
                "generator_start": data["generator_level_start"],
                "generator_stop": data["generator_level_stop"],
            })
        self.async_write_ha_state()


class VoltageEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_VOLT


class WattsEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
