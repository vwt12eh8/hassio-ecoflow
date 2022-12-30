from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ELECTRIC_CURRENT_AMPERE,
                                 ELECTRIC_POTENTIAL_VOLT, ENERGY_WATT_HOUR,
                                 FREQUENCY_HERTZ, PERCENTAGE, POWER_WATT,
                                 TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow
from reactivex import Observable

from . import (DOMAIN, EcoFlowData, EcoFlowDevice, EcoFlowEntity,
               EcoFlowExtraDevice, EcoFlowMainDevice)
from .ecoflow import is_delta, is_delta_mini, is_delta_pro, is_river, is_river_mini


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data: EcoFlowData = hass.data[DOMAIN]

    def device_added(device: EcoFlowDevice):
        entities = []
        if type(device) is EcoFlowMainDevice:
            entities.extend([
                CurrentEntity(device, device.inverter,
                            "ac_in_current", "AC input current"),
                CurrentEntity(device, device.inverter,
                              "ac_out_current", "AC output current"),
                EnergyEntity(device, device.pd, "ac_in_energy",
                             "AC input energy"),
                EnergyEntity(device, device.pd, "ac_out_energy",
                             "AC output energy"),
                EnergyEntity(device, device.pd, "car_in_energy",
                             "Car input energy"),
                EnergyEntity(device, device.pd, "dc_out_energy",
                             "DC output energy"),
                EnergyEntity(device, device.pd, "mppt_in_energy",
                             "MPPT input energy"),
                FanEntity(device, device.inverter, "fan_state", "Fan"),
                FrequencyEntity(device, device.inverter,
                                "ac_in_freq", "AC input frequency"),
                FrequencyEntity(device, device.inverter,
                                "ac_out_freq", "AC output frequency"),
                RemainEntity(device, device.pd, "remain_display", "Remain"),
                VoltageEntity(device, device.inverter,
                              "ac_in_voltage", "AC input voltage"),
                VoltageEntity(device, device.inverter,
                              "ac_out_voltage", "AC output voltage"),
                WattsEntity(device, device.pd, "in_power", "Total input"),
                WattsEntity(device, device.pd, "out_power", "Total output"),
                WattsEntity(device, device.inverter,
                            "ac_consumption", "AC output + loss", real=True),
                WattsEntity(device, device.inverter, "ac_out_power",
                            "AC output", real=False),
            ])
            if not is_river_mini(device.product):
                entities.extend([
                    WattsEntity(device, device.pd, "usb_out1_power",
                                "USB-A left output"),
                    WattsEntity(device, device.pd, "usb_out2_power",
                                "USB-A right output"),
                ])
            if is_delta(device.product):
                entities.extend([
                    CurrentEntity(device, device.mppt, "dc_in_current",
                                "DC input current"),
                    CyclesEntity(
                        device, device.bms, "battery_cycles", "Battery cycles"),
                    LevelEntity(device, device.pd, "battery_level",
                                "Total battery level"),
                    RemainEntity(device, device.ems,
                                 "battery_remain_charge", "Remain charge"),
                    RemainEntity(device, device.ems,
                                 "battery_remain_discharge", "Remain discharge"),
                    SingleLevelEntity(
                        device, device.bms, "battery_level_f32", "Battery level"),
                    TempEntity(device, device.inverter, "ac_out_temp",
                               "AC temperature"),
                    TempEntity(device, device.bms, "battery_temp",
                               "Battery temperature"),
                    TempEntity(device, device.mppt, "dc_in_temp",
                               "DC input temperature"),
                    TempEntity(device, device.mppt, "dc24_temp",
                               "DC output temperature"),
                    TempEntity(device, device.pd, "typec_out1_temp",
                               "USB-C left temperature"),
                    TempEntity(device, device.pd, "typec_out2_temp",
                               "USB-C right temperature"),
                    VoltageEntity(device, device.mppt, "dc_in_voltage",
                                  "DC input voltage"),
                    WattsEntity(device, device.inverter,
                                "ac_in_power", "AC input"),
                    WattsEntity(device, device.mppt, "dc_in_power",
                                "DC input", real=True),
                    WattsEntity(device, device.mppt,
                                "car_consumption", "Car output + loss", real=True),
                    WattsEntity(device, device.mppt,
                                "car_out_power", "Car output"),
                ])
                if is_delta_mini(device.product):
                    entities.extend([
                        WattsEntity(device, device.pd,
                                    "usbqc_out1_power", "USB-Fast output"),
                        WattsEntity(device, device.pd,
                                    "typec_out1_power", "USB-C output"),
                    ])
                else:
                    entities.extend([
                        WattsEntity(device, device.pd, "usbqc_out1_power",
                                    "USB-Fast left output"),
                        WattsEntity(device, device.pd, "usbqc_out2_power",
                                    "USB-Fast right output"),
                        WattsEntity(device, device.pd, "typec_out1_power",
                                    "USB-C left output"),
                        WattsEntity(device, device.pd, "typec_out2_power",
                                    "USB-C right output"),
                    ])
                if is_delta_pro(device.product):
                    entities.extend([
                        WattsEntity(device, device.mppt,
                                    "anderson_out_power", "Anderson output"),
                    ])
            if is_river(device.product):
                entities.extend([
                    CurrentEntity(device, device.inverter, "dc_in_current",
                                "DC input current"),
                    CyclesEntity(device, device.ems, "battery_cycles",
                                 "Battery cycles"),
                    LevelEntity(device, device.pd, "battery_level",
                                "Total battery level"),
                    SingleLevelEntity(device, device.ems, "battery_main_level",
                                      "Battery level"),
                    TempEntity(device, device.inverter, "ac_in_temp",
                               "AC input temperature"),
                    TempEntity(device, device.inverter, "ac_out_temp",
                               "AC output temperature"),
                    TempEntity(device, device.ems, "battery_main_temp",
                               "Battery temperature"),
                    TempEntity(device, device.pd, "car_out_temp",
                               "DC output temperature"),
                    TempEntity(device, device.pd, "typec_out1_temp",
                               "USB-C temperature"),
                    VoltageEntity(device, device.inverter, "dc_in_voltage",
                                  "DC input voltage"),
                    WattsEntity(device, device.pd,
                                "car_out_power", "Car output"),
                    WattsEntity(device, device.pd,
                                "light_power", "Light output"),
                    WattsEntity(device, device.pd, "usbqc_out1_power",
                                "USB-Fast output"),
                    WattsEntity(device, device.pd, "typec_out1_power",
                                "USB-C output"),
                ])
            if is_river_mini(device.product):
                entities.extend([
                        CurrentEntity(device, device.inverter, "dc_in_current",
                                    "DC input current"),
                        CyclesEntity(device, device.inverter, "battery_cycles",
                                 "Battery cycles"),
                        LevelEntity(device, device.pd, "battery_level",
                                    "Total battery level"),
                        TempEntity(device, device.inverter, "ac_in_temp",
                                   "AC input temperature"),
                        TempEntity(device, device.inverter, "ac_out_temp",
                                   "AC output temperature"),
                        TempEntity(device, device.inverter, "battery_main_temp",
                                   "Battery temperature"),
                        TempEntity(device, device.pd, "car_out_temp",
                                   "Car output temperature"),
                        VoltageEntity(device, device.inverter, "dc_in_voltage",
                                      "Car input voltage"),
                        WattsEntity(device, device.pd, "usb_out1_power",
                                "USB-A output"),
                        WattsEntity(device, device.pd,
                                    "car_out_power", "Car output"),
                        VoltageEntity(device, device.inverter, "battery_main_voltage",
                                    "Battery voltage"),
                    ])
        elif type(device) is EcoFlowExtraDevice:
            if is_delta(device.product):
                entities.extend([
                    CyclesEntity(
                        device, device.bms, "battery_cycles", "Battery cycles"),
                    SingleLevelEntity(
                        device, device.bms, "battery_level_f32", "Battery level"),
                    TempEntity(device, device.bms, "battery_temp",
                               "Battery temperature"),
                ])
            elif is_river(device.product):
                entities.extend([
                    CyclesEntity(device, device.bms, "battery_cycles",
                                "Battery cycles"),
                    SingleLevelEntity(
                        device, device.bms, "battery_level", "Battery level"),
                    TempEntity(device, device.bms, "battery_temp",
                               "Battery temperature"),
                ])
        async_add_entities(entities)

    entry.async_on_unload(data.device_added.subscribe(device_added).dispose)
    for device in data.devices.values():
        device_added(device)


class BaseEntity(SensorEntity, EcoFlowEntity):
    def _on_updated(self, data: dict[str, Any]):
        self._attr_native_value = data[self._key]


class CurrentEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ELECTRIC_CURRENT_AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT


class CyclesEntity(BaseEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-heart-variant"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING


class EnergyEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING


class FanEntity(BaseEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def icon(self):
        value = self.native_value
        if value is None or self.native_value <= 0:
            return "mdi:fan-off"
        return "mdi:fan"


class FrequencyEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = FREQUENCY_HERTZ
    _attr_state_class = SensorStateClass.MEASUREMENT


class LevelEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: EcoFlowDevice, src: Observable[dict[str, Any]], key: str, name: str):
        super().__init__(device, src, key, name)
        self._attr_extra_state_attributes = {}


class RemainEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def _on_updated(self, data: dict[str, Any]):
        value: timedelta = data[self._key]
        if value.total_seconds() == 8639940:
            self._attr_native_value = None
        else:
            self._attr_native_value = utcnow() + value


class SingleLevelEntity(LevelEntity):
    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        if "battery_capacity_remain" in data:
            self._attr_extra_state_attributes["capacity_remain"] = data["battery_capacity_remain"]
        if "battery_capacity_full" in data:
            self._attr_extra_state_attributes["capacity_full"] = data["battery_capacity_full"]
        if "battery_capacity_design" in data:
            self._attr_extra_state_attributes["capacity_design"] = data["battery_capacity_design"]


class TempEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT


class VoltageEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT


class WattsEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: EcoFlowDevice, src: Observable[dict[str, Any]], key: str, name: str, real: bool | int = False):
        super().__init__(device, src, key, name)
        if key.endswith("_consumption"):
            self._key = key[:-11] + "out_power"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._real = real

    def _on_updated(self, data: dict[str, Any]):
        key = self._key[:-5]
        if self._real is not False and f"{key}current" in data and f"{key}voltage" in data:
            self._attr_native_value = (
                data[f"{key}current"] * data[f"{key}voltage"])
            if self._real is not True:
                self._attr_native_value = round(
                    self._attr_native_value, self._real)
                if self._real == 0:
                    self._attr_native_value = int(self._attr_native_value)
        else:
            super()._on_updated(data)
