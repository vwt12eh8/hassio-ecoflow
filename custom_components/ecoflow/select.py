from typing import Callable

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow.local import send

_FREQS = {
    "50Hz": 1,
    "60Hz": 2,
}

_DC_IMPUTS = {
    "Auto": 0,
    "MPPT": 1,
    "DC": 2,
}

_DC_ICONS = {
    "Auto": None,
    "MPPT": "mdi:solar-power",
    "DC": "mdi:current-dc",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        FreqEntity(client),
        DcInModeEntity(client),
    ])


class FreqEntity(EcoFlowEntity[dict], SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:sine-wave"
    _attr_options = list(_FREQS.keys())

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, "inv")
        self._attr_name += " AC output frequency"
        self._attr_unique_id += "-cfg_ac_out_freq"

    @property
    def current_option(self):
        value = self.coordinator.data.get("cfg_ac_out_freq", None)
        return next((i for i in _FREQS if _FREQS[i] == value), None)

    async def async_select_option(self, option: str):
        value = _FREQS[option]
        await self._client.request(send.set_ac_out(
            self._client.product, freq=value))
        await self.coordinator.async_request_refresh()


class DcInModeEntity(EcoFlowEntity[dict], SelectEntity):
    _attr_current_option = None
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(_DC_IMPUTS.keys())

    def __init__(self, client: HassioEcoFlowClient):
        super().__init__(client, "dc_in_mode")
        self._attr_name += " DC input mode"
        self._attr_unique_id += "-dc_in_mode"

    @property
    def current_option(self):
        value = self.coordinator.data
        return next((i for i in _DC_IMPUTS if _DC_IMPUTS[i] == value), None)

    @property
    def icon(self):
        return _DC_ICONS.get(self.current_option, None)

    async def async_select_option(self, option: str):
        value = _DC_IMPUTS[option]
        await self._client.request(send.set_dc_in_mode(
            self._client.product, value))
        await self.coordinator.async_request_refresh()
