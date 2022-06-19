from typing import Any, Callable

from homeassistant.components.light import COLOR_MODE_ONOFF, SUPPORT_EFFECT, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN, EcoFlowEntity, HassioEcoFlowClient
from .ecoflow import is_river, send

_EFFECTS = ["Low", "High", "SOS"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if is_river(client.product):
        entities.extend([
            LedEntity(client, client.pd, "light_state", "Light"),
        ])

    async_add_entities(entities)


class LedEntity(LightEntity, EcoFlowEntity):
    _attr_effect = _EFFECTS[0]
    _attr_effect_list = _EFFECTS
    _attr_supported_color_modes = {COLOR_MODE_ONOFF}
    _attr_supported_features = SUPPORT_EFFECT

    def _on_updated(self, data: dict[str, Any]):
        value = data[self._key]
        if value != 0:
            self._attr_is_on = True
            self._attr_effect = _EFFECTS[value - 1]
        else:
            self._attr_is_on = False
            self._attr_effect = None

    async def async_turn_off(self, **kwargs):
        self._client.tcp.write(send.set_light(self._client.product, 0))

    async def async_turn_on(self, effect: str = None, **kwargs):
        if not effect:
            effect = self.effect or _EFFECTS[0]
        self._client.tcp.write(send.set_light(
            self._client.product, _EFFECTS.index(effect) + 1))
