from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN, HassioEcoFlowClient


def _to_serializable(x):
    if type(x) is timedelta:
        x = x.total_seconds()
    return x


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    values = {}
    for i in client.diagnostics:
        d = client.diagnostics[i]
        values[i] = {x: _to_serializable(d[x]) for x in d}
    return values
