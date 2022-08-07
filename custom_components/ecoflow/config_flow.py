import reactivex.operators as ops
import voluptuous as vol
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_MAC

from . import CONF_PRODUCT, DOMAIN, request
from .ecoflow import PORT, PRODUCTS, receive, send
from .ecoflow.rxtcp import RxTcpAutoConnection


class EcoflowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 2
    host = None
    mac = None

    async def _get_serial_main(self):
        async with RxTcpAutoConnection(self.host, PORT) as tcp:
            received = tcp.received.pipe(
                receive.merge_packet(),
                ops.map(receive.decode_packet),
                ops.filter(receive.is_serial_main),
                ops.map(lambda x: receive.parse_serial(x[3])),
            )
            await tcp.wait_opened()
            info = await request(tcp, send.get_serial_main(), received)

        if info["product"] not in PRODUCTS:
            return self.async_abort(reason="product_unsupported")

        serial = info["serial"]
        entry = await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
        if entry and serial in entry.data:
            data = dict(entry.data[serial])
            data[CONF_HOST] = self.host
            if self.mac:
                data[CONF_MAC] = self.mac
            self._abort_if_unique_id_configured({serial: data}, False)
        await self.async_set_unique_id(serial)

        return info

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo):
        self.host = discovery_info.ip
        self.mac = discovery_info.macaddress
        await self._get_serial_main()
        return self.async_show_form(step_id="user")

    async def async_step_user(self, user_input: dict = None):
        if user_input:
            self.host = user_input.get(CONF_HOST)

        errors = {}
        if self.host and user_input is not None:
            try:
                info = await self._get_serial_main()
            except TimeoutError:
                errors["base"] = "timeout"
            else:
                serial = info["serial"]
                entry = await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
                if entry and serial in entry.data:
                    data = dict(entry.data[serial])
                else:
                    data = {}
                data.update({
                    CONF_HOST: self.host,
                    CONF_PRODUCT: info["product"],
                })
                if self.mac:
                    data[CONF_MAC] = self.mac

                self._abort_if_unique_id_configured({serial: data}, False)
                return self.async_create_entry(
                    title="",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=self.host): str,
            }),
            last_step=True,
        )
