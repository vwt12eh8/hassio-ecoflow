import reactivex.operators as ops
import voluptuous as vol
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_MAC

from . import CONF_PRODUCT, DOMAIN, request
from .ecoflow import PORT, PRODUCTS, receive, send
from .ecoflow.rxtcp import RxTcpAutoConnection


class EcoflowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    host = None
    mac = None

    async def _get_serial_main(self):
        tcp = RxTcpAutoConnection(self.host, PORT)
        received = tcp.received.pipe(
            receive.merge_packet(),
            ops.map(receive.decode_packet),
            ops.filter(receive.is_serial_main),
            ops.map(lambda x: receive.parse_serial(x[3])),
        )
        try:
            await tcp.wait_opened()
            info = await request(tcp, send.get_serial_main(), received)
        finally:
            tcp.close()
        if info["product"] not in PRODUCTS:
            return self.async_abort(reason="product_unsupported", description_placeholders={"product": info["product"]})
        await self.async_set_unique_id(info["serial"])
        self._abort_if_unique_id_configured(updates={
            CONF_HOST: self.host,
            CONF_MAC: self.mac,
        })
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
                pn = PRODUCTS.get(info["product"], "")
                if pn != "":
                    pn += " "
                return self.async_create_entry(
                    title=f'{pn}{info["serial"][-6:]}',
                    data={
                        CONF_HOST: self.host,
                        CONF_MAC: self.mac,
                        CONF_PRODUCT: info["product"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=self.host): str,
            }),
            last_step=True,
        )
