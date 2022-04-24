from typing import Callable

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow.local import send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AcOutputEntity(client),
        XboostEntity(client),
        DcOutputEntity(client),
        AutoFanEntity(client),
        SilenceEntity(client),
    ])


class AutoFanEntity(EcoFlowEntity[dict], SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, "fan_auto")
        self._attr_name += " auto fan speed"
        self._attr_unique_id += "-fan_auto"

    @property
    def icon(self):
        return "mdi:fan-auto" if self.is_on else "mdi:fan-chevron-up"

    @property
    def is_on(self):
        return self.coordinator.data

    async def async_turn_off(self, **kwargs):
        await self._client.request(send.set_fan_auto(self._client.product, False))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._client.request(send.set_fan_auto(self._client.product, True))
        await self.coordinator.async_request_refresh()


class BaseOutputEntity(EcoFlowEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET
    _key: str
    _mod: str
    _name: str

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, self._mod)
        self._attr_name += f" {self._name}"
        self._attr_unique_id += f"-{self._key}"

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self._key, False))


class AcOutputEntity(BaseOutputEntity):
    _key = "ac_out"
    _mod = "inv"
    _name = "AC output"

    async def async_turn_off(self, **kwargs):
        await self._client.request(send.set_ac_out(self._client.product, False))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._client.request(send.set_ac_out(self._client.product, True))
        await self.coordinator.async_request_refresh()


class SilenceEntity(BaseOutputEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _key = "silence_charge"
    _mod = "inv"
    _name = "AC silence charge"

    @property
    def icon(self):
        return "mdi:fan-chevron-down" if self.is_on else "mdi:fan-auto"

    async def async_turn_off(self, **kwargs):
        await self._client.request(send.set_silence_charge(self._client.product, False))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._client.request(send.set_silence_charge(self._client.product, True))
        await self.coordinator.async_request_refresh()


class XboostEntity(BaseOutputEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _key = "xboost"
    _mod = "inv"
    _name = "AC X-Boost"

    async def async_turn_off(self, **kwargs):
        await self._client.request(send.set_ac_out(self._client.product, xboost=False))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._client.request(send.set_ac_out(self._client.product, xboost=True))
        await self.coordinator.async_request_refresh()


class DcOutputEntity(BaseOutputEntity):
    _key = "dc_out"
    _mod = "pd"
    _name = "DC output"

    async def async_turn_off(self, **kwargs):
        await self._client.request(send.set_dc_out(self._client.product, False))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._client.request(send.set_dc_out(self._client.product, True))
        await self.coordinator.async_request_refresh()
