from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN, HassioEcoFlowClient


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    client: HassioEcoFlowClient = hass.data[DOMAIN][entry.entry_id]
    return {
        "product": entry.data["product"],
        "pd": client.pd.data,
        "inv": client.inv.data,
        "bms_main": client.bms_main.data,
        "bms_extra": client.bms_extra.data,
        "dc_in_mode": client.dc_in_mode.data,
        "fan_auto": client.fan_auto.data,
    }
