from datetime import timedelta
from typing import Callable

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ELECTRIC_CURRENT_MILLIAMPERE,
                                 ELECTRIC_POTENTIAL_MILLIVOLT,
                                 ENERGY_WATT_HOUR, FREQUENCY_HERTZ, PERCENTAGE,
                                 POWER_WATT, TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = [
        BmsLevelEntity(client, "bms_main"),
        LevelEntity(client),

        WattsEntity(client, "inv", "in_watts", "input"),
        WattsEntity(client, "inv", "ac_out_watts", "AC output"),
        WattsEntity(client, "pd", "dc_out_watts", "DC output"),
        WattsEntity(client, "pd", "typec1_watts", "Type-C1 output"),
        WattsEntity(client, "pd", "usb1_watts", "USB1 output"),
        WattsEntity(client, "pd", "usb2_watts", "USB2 output"),
        WattsEntity(client, "pd", "usbqc1_watts", "USB-QC1 output"),
        WattsEntity(client, "pd", "led_watts", "light output"),

        FanStateEntity(client, "inv", "fan_state", "fan speed"),

        TempEntity(client, "inv", "ac_in_temp", "AC input temperature"),
        TempEntity(client, "inv", "ac_out_temp", "AC output temperature"),
        TempEntity(client, "pd", "dc_out_temp", "DC temperature"),
        TempEntity(client, "pd", "typec1_temp", "Type-C1 temperature"),
        TempEntity(client, "bms_main", "temp", "battery temperature"),

        VolEntity(client, "inv", "ac_in_vol", "AC input voltage"),
        VolEntity(client, "inv", "ac_out_vol", "AC output voltage"),
        VolEntity(client, "bms_main", "vol", "battery voltage"),

        AmpEntity(client, "inv", "ac_in_amp", "AC input current"),
        AmpEntity(client, "inv", "ac_out_amp", "AC output current"),

        FreqEntity(client, "inv", "ac_out_freq", "AC output frequency"),
        FreqEntity(client, "inv", "ac_in_freq", "AC input frequency"),

        EnergyEntity(client, "pd", "chg_power_mppt", "MPPT total input"),
        EnergySumEntity(client, "pd", "chg_sum", "total charged", {
            "chg_power_dc": "dc",
            "chg_power_mppt": "mppt",
            "chg_power_ac": "ac",
        }),
        EnergySumEntity(client, "pd", "dsg_sum", "total discharged", {
            "dsg_power_dc": "dc",
            "dsg_power_ac": "ac",
        }),

        BmsCycleEntity(client, "bms_main"),

        UsedTimeEntity(client, "pd", "ac_out_used_time", "AC output used"),
        UsedTimeEntity(client, "pd", "dc_in_used_time", "DC input used"),
        UsedTimeEntity(client, "pd", "mppt_used_time", "MPPT input used"),
        UsedTimeEntity(client, "pd", "dc_out_used_time", "DC output used"),
        UsedTimeEntity(client, "pd", "typec_used_time", "Type-C output used"),
        UsedTimeEntity(client, "pd", "usb_used_time", "USB output used"),
        UsedTimeEntity(client, "pd", "usbqc_used_time", "USB QC output used"),
    ]
    if 12 < client.product < 15:  # DELTA Max/Pro
        entities.extend([
            WattsEntity(client, "pd", "typec2_watts", "Type-C2 output"),
            TempEntity(client, "pd", "typec2_temp", "Type-C2 temperature"),
            WattsEntity(client, "pd", "usbqc2_watts", "USB-QC2 output"),
        ])
    async_add_entities(entities)

    extras = set[str]()

    def extra_updated():
        if client.serial_extra is None:
            return
        if client.serial_extra in extras:
            return
        extras.add(client.serial_extra)
        async_add_entities([
            BmsLevelEntity(client, "bms_extra"),
            TempEntity(client, "bms_extra", "temp", "battery temperature"),
            VolEntity(client, "bms_extra", "vol", "battery voltage"),
            BmsCycleEntity(client, "bms_extra"),
        ])
    entry.async_on_unload(client.bms_extra.async_add_listener(extra_updated))


class AmpEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = ELECTRIC_CURRENT_MILLIAMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class BmsCycleEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-heart-outline"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, client: HassioEcoFlowClient, module: str):
        super().__init__(client, module)
        self._attr_name += " battery cycles"
        self._attr_unique_id += "-bms-cycles"

    @property
    def native_value(self):
        return self.coordinator.data.get("cycles", None)


class EnergyEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class EnergySumEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str, keys: dict[str]):
        super().__init__(client, module)
        self._keys = keys
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {self._keys[i]: data[i] for i in self._keys if i in data}

    @property
    def native_value(self):
        return sum(self.extra_state_attributes.values())


class FanStateEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fan"

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class FreqEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = FREQUENCY_HERTZ
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class LevelEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, "pd")
        self._attr_name += " total battery level"
        self._attr_unique_id += "-pd-soc"

    @property
    def native_value(self):
        return self.coordinator.data.get("soc_sum", None)


class BmsLevelEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str):
        super().__init__(client, module)
        self._attr_name += " battery level"
        self._attr_unique_id += "-bms-soc"

    @property
    def native_value(self):
        return self.coordinator.data.get("soc", None)


class TempEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class UsedTimeEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:history"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return timedelta(seconds=self.coordinator.data.get(self._key, 0))


class VolEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_MILLIVOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)


class WattsEntity(EcoFlowEntity[dict], SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HassioEcoFlowClient, module: str, key: str, name: str):
        super().__init__(client, module)
        self._key = key
        self._attr_name += " " + name
        self._attr_unique_id += f"-{module}-{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key, None)
