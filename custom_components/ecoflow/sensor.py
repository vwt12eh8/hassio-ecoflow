from typing import Any, Callable, Optional

import reactivex.operators as ops
from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ELECTRIC_CURRENT_AMPERE,
                                 ELECTRIC_POTENTIAL_VOLT, ENERGY_WATT_HOUR,
                                 FREQUENCY_HERTZ, PERCENTAGE, POWER_WATT,
                                 TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from reactivex import Observable

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient, select_bms
from .ecoflow import (is_delta, is_delta_mini, is_delta_pro, is_power_station,
                      is_river)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_power_station(client.product):
        entities.extend([
            CurrentEntity(client, client.inverter,
                          "ac_in_current", "AC Input Current"),
            CurrentEntity(client, client.inverter,
                          "ac_out_current", "AC Output Current"),
            EnergyEntity(client, client.pd, "mppt_in_energy",
                         "MPPT Input Energy"),
            EnergySumEntity(client, "in_energy", [
                            "ac", "car", "mppt"], "Total Input Energy"),
            EnergySumEntity(client, "out_energy", [
                            "ac", "car"], "Total Output Energy"),
            FanEntity(client, client.inverter, "fan_state", "Fan"),
            FrequencyEntity(client, client.inverter,
                            "ac_in_freq", "AC Input Frequency"),
            FrequencyEntity(client, client.inverter,
                            "ac_out_freq", "AC Output Frequency"),
            TotalLevelEntity(client, client.pd, "battery_level",
                             "Battery"),
            VoltageEntity(client, client.inverter,
                          "ac_in_voltage", "AC Input Voltage"),
            VoltageEntity(client, client.inverter,
                          "ac_out_voltage", "AC Output Voltage"),
            WattsEntity(client, client.pd, "in_power", "Total Input"),
            WattsEntity(client, client.pd, "out_power", "Total Output"),
            WattsEntity(client, client.inverter, "ac_out_power", "AC Output"),
            WattsEntity(client, client.pd, "usb_out1_power",
                        "USB-A Left Output"),
            WattsEntity(client, client.pd, "usb_out2_power",
                        "USB-A Right Output"),
        ])
        if is_delta(client.product):
            bms = (
                client.bms.pipe(select_bms(0), ops.share()),
                client.bms.pipe(select_bms(1), ops.share()),
                client.bms.pipe(select_bms(2), ops.share()),
            )
            entities.extend([
                CurrentEntity(client, client.mppt, "dc_in_current",
                              "DC Input Current"),
                CyclesEntity(
                    client, bms[0], "battery_cycles", "Main Battery Cycles", 0),
                SingleLevelEntity(
                    client, bms[0], "battery_level_f32", "Main Battery", 0),
                TempEntity(client, client.inverter, "ac_out_temp",
                           "AC Temperature"),
                TempEntity(client, bms[0], "battery_temp",
                           "Main Battery Temperature", 0),
                TempEntity(client, client.mppt, "dc_in_temp",
                           "DC Input Temperature"),
                TempEntity(client, client.mppt, "dc24_temp",
                           "DC Output Temperature"),
                TempEntity(client, client.pd, "typec_out1_temp",
                           "USB-C Left Temperature"),
                TempEntity(client, client.pd, "typec_out2_temp",
                           "USB-C Right Temperature"),
                VoltageEntity(client, client.mppt, "dc_in_voltage",
                              "DC Input Voltage"),
                WattsEntity(client, client.inverter,
                            "ac_in_power", "AC Input"),
                WattsEntity(client, client.mppt, "dc_in_power", "DC Input"),
                WattsEntity(client, client.mppt, "car_out_power", "DC Output"),
            ])
            if is_delta_mini(client.product):
                entities.extend([
                    WattsEntity(client, client.pd,
                                "usbqc_out1_power", "USB-Fast Output"),
                    WattsEntity(client, client.pd,
                                "typec_out1_power", "USB-C Output"),
                ])
            else:
                entities.extend([
                    CyclesEntity(
                        client, bms[1], "battery_cycles", "Extra1 Battery Cycles", 1),
                    CyclesEntity(
                        client, bms[2], "battery_cycles", "Extra2 Battery Cycles", 2),
                    SingleLevelEntity(
                        client, bms[1], "battery_level_f32", "Extra1 Battery", 1),
                    SingleLevelEntity(
                        client, bms[2], "battery_level_f32", "Extra2 Battery", 2),
                    TempEntity(client, bms[1], "battery_temp",
                               "Extra1 Battery Temperature", 1),
                    TempEntity(client, bms[2], "battery_temp",
                               "Extra2 Battery Temperature", 2),
                    WattsEntity(client, client.pd, "usbqc_out1_power",
                                "USB-Fast Left Output"),
                    WattsEntity(client, client.pd, "usbqc_out2_power",
                                "USB-Fast Right Output"),
                    WattsEntity(client, client.pd, "typec_out1_power",
                                "USB-C Left Output"),
                    WattsEntity(client, client.pd, "typec_out2_power",
                                "USB-C Right Output"),
                ])
            if is_delta_pro(client.product):
                entities.extend([
                    WattsEntity(client, client.mppt,
                                "anderson_out_power", "Anderson Output"),
                ])
        if is_river(client.product):
            extra = client.bms.pipe(select_bms(1), ops.share())
            entities.extend([
                CurrentEntity(client, client.inverter, "dc_in_current",
                              "DC Input Current"),
                CyclesEntity(client, client.ems, "battery_cycles",
                             "Main Battery Cycles"),
                CyclesEntity(client, extra, "battery_cycles",
                             "Extra Battery Cycles", 1),
                SingleLevelEntity(client, client.ems, "battery_main_level",
                            "Main Battery"),
                SingleLevelEntity(
                    client, extra, "battery_level", "Extra Battery", 1),
                TempEntity(client, client.inverter, "ac_in_temp",
                           "AC Input Temperature"),
                TempEntity(client, client.inverter, "ac_out_temp",
                           "AC Output Temperature"),
                TempEntity(client, client.ems, "battery_main_temp",
                           "Main Battery Temperature"),
                TempEntity(client, extra, "battery_temp",
                           "Extra Battery Temperature", 1),
                TempEntity(client, client.pd, "car_out_temp",
                           "DC Output Temperature"),
                TempEntity(client, client.pd, "typec_out1_temp",
                           "USB-C Temperature"),
                VoltageEntity(client, client.inverter, "dc_in_voltage",
                              "DC Input Voltage"),
                WattsEntity(client, client.pd, "car_out_power", "DC Output"),
                WattsEntity(client, client.pd, "light_power", "Light Output"),
                WattsEntity(client, client.pd, "usbqc_out1_power",
                            "USB-Fast Output"),
                WattsEntity(client, client.pd, "typec_out1_power",
                            "USB-C Output"),
            ])

    async_add_entities(entities)


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


class EnergySumEntity(EnergyEntity):
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


class FrequencyEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = FREQUENCY_HERTZ
    _attr_state_class = SensorStateClass.MEASUREMENT


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


class TotalLevelEntity(LevelEntity):
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self._client.ems, self.__ems_updated)

    def _on_updated(self, data: dict[str, Any]):
        super()._on_updated(data)
        self._attr_extra_state_attributes["remain"] = data["remain_display"].__str__(
        )

    def __ems_updated(self, data: dict[str, Any]):
        if "battery_remain_charge" in data:
            self._attr_extra_state_attributes.update({
                "remain_charge": data["battery_remain_charge"].__str__(),
                "remain_discharge": data["battery_remain_discharge"].__str__(),
            })
            self.async_write_ha_state()


class VoltageEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT


class WattsEntity(BaseEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
