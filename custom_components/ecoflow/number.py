from typing import Callable

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow.local import send


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        MaxLevelEntity(client),
    ])


class MaxLevelEntity(EcoFlowEntity[dict], NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_max_value = 100
    _attr_min_value = 30
    _attr_mode = NumberMode.SLIDER

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, "bms_main")
        self._attr_name += " max charge level"
        self._attr_unique_id += "-max_chg_soc"

    @property
    def icon(self):
        return "mdi:battery-lock-open" if self.value == self.max_value else "mdi:battery-lock"

    @property
    def value(self):
        return self.coordinator.data.get("max_chg_soc", None)

    async def async_set_value(self, value: float):
        await self._client.request(send.set_ups(self._client.product, int(value)))
        await self.coordinator.async_request_refresh()
