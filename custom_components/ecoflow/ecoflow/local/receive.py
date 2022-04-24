from typing import TypedDict

from . import command


def _ver_str(data):
    return ".".join(str(i) for i in data)


def bms_main(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return bms_main_river(d)
    if 12 < product < 16:
        return bms_main_delta(d)
    if product == 17:
        return bms_main_river_mini(d)


def bms_main_delta(d: bytes):
    # TODO
    return {}


def bms_main_river(d: bytes):
    return {
        "error_code": int.from_bytes(d[0:4], "little"),
        "sys_ver": _ver_str(reversed(d[4:8])),
        "soc": d[8],
        "vol": int.from_bytes(d[9:11], "little"),
        "amp": int.from_bytes(d[13:15], "little"),
        "temp": d[17],
        "state": d[18],
        "remain_cap": int.from_bytes(d[19:23], "little"),
        "full_cap": int.from_bytes(d[23:27], "little"),
        "cycles": int.from_bytes(d[27:31], "little"),
        "max_chg_soc": d[31],
    }


def bms_main_river_mini(d: bytes):
    # TODO
    return {}


def bms_extra(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return bms_extra_river(d)
    if 12 < product < 16:
        return bms_extra_delta(d)


def bms_extra_river(d: bytes):
    return {
        "error_code": int.from_bytes(d[0:4], "little"),
        "sys_ver": _ver_str(reversed(d[4:8])),
        "soc": d[8],
        "vol": int.from_bytes(d[9:11], "little"),
        "amp": int.from_bytes(d[13:15], "little"),
        "temp": d[17],
        "remain_cap": int.from_bytes(d[18:22], "little"),
        "full_cap": int.from_bytes(d[22:26], "little"),
        "cycles": int.from_bytes(d[26:30], "little"),
        "ambient_light_mode": d[30],
        "ambient_light_animate": d[31],
        "ambient_light_color": list(d[32:36]),
        "ambient_light_brightness": d[36],
    }


def bms_extra_delta(d: bytes):
    # TODO
    return {}


def dc_in_mode(d: bytes, product: int = None):
    return d[1]


def fan_auto(d: bytes, product: int = None):
    return d[0] == 1


def inv(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return inv_river(d)
    if 12 < product < 16:
        return inv_delta(d)
    if product == 17:
        return inv_river_mini(d)


def inv_delta(d: bytes):
    # TODO
    return {}


def inv_river(d: bytes):
    return {
        "error_code": int.from_bytes(d[0:4], "little"),
        "sys_ver": _ver_str(reversed(d[4:8])),
        "chg_type": d[8],
        "in_watts": int.from_bytes(d[9:11], "little"),
        "ac_out_watts": int.from_bytes(d[11:13], "little"),
        "inv_type": d[13],
        "ac_out_vol": int.from_bytes(d[14:18], "little"),
        "ac_out_amp": int.from_bytes(d[18:22], "little"),
        "ac_out_freq": d[22],
        "ac_in_vol": int.from_bytes(d[23:27], "little"),
        "ac_in_amp": int.from_bytes(d[27:31], "little"),
        "ac_in_freq": d[31],
        "ac_out_temp": d[32],
        "dc_in_vol": int.from_bytes(d[33:37], "little"),
        "dc_in_amp": int.from_bytes(d[37:41], "little"),
        "ac_in_temp": d[41],
        "fan_state": d[42],
        "ac_out": d[43],
        "xboost": d[44],
        "cfg_ac_out_vol": int.from_bytes(d[45:49], "little"),
        "cfg_ac_out_freq": d[49],
        "silence_charge": d[50],
    }


def inv_river_mini(d: bytes):
    # TODO
    return {}


def pd(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return pd_river(d)
    if 12 < product < 16:
        return pd_delta(d)
    if product == 17:
        return pd_river_mini(d)


def pd_delta(d: bytes):
    # TODO
    return {}


def pd_river(d: bytes):
    return {
        "model": d[0],
        "error_code": int.from_bytes(d[1:5], "little"),
        "sys_ver": _ver_str(reversed(d[5:9])),
        "soc_sum": d[9],
        "watts_out_sum": int.from_bytes(d[10:12], "little"),
        "watts_in_sum": int.from_bytes(d[12:14], "little"),
        "remain_time": int.from_bytes(d[14:18], "little"),
        "dc_out": d[18],
        "light_state": d[19],
        "beep": d[20],
        "typec_watts": d[21],
        "usb1_watts": d[22],
        "usb2_watts": d[23],
        "usbqc_watts": d[24],
        "dc_out_watts": d[25],
        "led_watts": d[26],
        "typec_temp": d[27],
        "dc_out_temp": d[28],
        "standby_min": int.from_bytes(d[29:31], "little"),
        "chg_power_dc": int.from_bytes(d[31:35], "little"),
        "chg_power_mppt": int.from_bytes(d[35:39], "little"),
        "chg_power_ac": int.from_bytes(d[39:43], "little"),
        "dsg_power_dc": int.from_bytes(d[43:46], "little"),
        "dsg_power_ac": int.from_bytes(d[47:51], "little"),
        "usb_used_time": int.from_bytes(d[51:55], "little"),
        "usbqc_used_time": int.from_bytes(d[55:59], "little"),
        "typec_used_time": int.from_bytes(d[59:63], "little"),
        "dc_out_used_time": int.from_bytes(d[63:67], "little"),
        "ac_out_used_time": int.from_bytes(d[67:71], "little"),
        "dc_in_used_time": int.from_bytes(d[71:75], "little"),
        "mppt_used_time": int.from_bytes(d[75:79], "little"),
    }


def pd_river_mini(d: bytes):
    return {
        "model": d[0],
        "error_code": int.from_bytes(d[1:5], "little"),
        "sys_ver": _ver_str(reversed(d[5:9])),
        "wifi_ver": _ver_str(reversed(d[9:13])),
        "wifi_auto_recovery": d[13],
        "soc_sum": d[14],
        "watts_out_sum": int.from_bytes(d[14:16], "little"),
        "watts_in_sum": int.from_bytes(d[16:18], "little"),
        "remain_time": int.from_bytes(d[18:22], "little"),
        "beep": d[22],
        "dc_out": d[23],
        "usb1_watts": d[24],
        "usb2_watts": d[25],
        "usbqc1_watts": d[26],
        "usbqc2_watts": d[27],
        "typec1_watts": d[28],
        "typec2_watts": d[29],
        "typec1_temp": d[30],
        "typec2_temp": d[31],
        "dc_out_watts": d[32],
        "dc_out_temp": d[33],
        "standby_min": int.from_bytes(d[34:36], "little"),
        "lcd_min": int.from_bytes(d[36:38], "little"),
        "lcd_brightness": d[38],
        "chg_power_dc": int.from_bytes(d[39:43], "little"),
        "chg_power_mppt": int.from_bytes(d[43:47], "little"),
        "chg_power_ac": int.from_bytes(d[47:51], "little"),
        "dsg_power_dc": int.from_bytes(d[51:55], "little"),
        "dsg_power_ac": int.from_bytes(d[55:59], "little"),
        "usb_used_time": int.from_bytes(d[59:63], "little"),
        "usbqc_used_time": int.from_bytes(d[63:67], "little"),
        "typec_used_time": int.from_bytes(d[67:71], "little"),
        "dc_out_used_time": int.from_bytes(d[71:75], "little"),
        "ac_out_used_time": int.from_bytes(d[75:79], "little"),
        "dc_in_used_time": int.from_bytes(d[79:83], "little"),
        "mppt_used_time": int.from_bytes(d[83:87], "little"),
        # "reserved": d[87:92],
        "sys_chg_flag": d[92],
        "wifi_rssi": d[93],
        "wifi_watts": d[94],
    }


def product_info(d: bytes, product: int = None):
    return {
        "product": int.from_bytes(d[0:2], "little"),
        "product_detail": int.from_bytes(d[2:4], "little"),
        "app_ver": _ver_str(d[4:8]),
        "loader_ver": _ver_str(reversed(d[8:12])),
    }


class Sn(TypedDict):
    chk_val: int
    product: int
    product_detail: int
    model: int
    serial: str
    cpu_id: str


def sn(d: bytes, product: int = None):
    return Sn(
        chk_val=int.from_bytes(d[0:4], "little"),
        product=d[4],
        product_detail=d[6],
        model=d[7],
        serial=d[8:23].decode("utf-8"),
        cpu_id=d[24:36].decode("utf-8"),
    )


def dc_input_current(d: bytes, product: int = None):
    return int.from_bytes(d, "little")


PARSERS = {
    command.product_info_pd: product_info,
    command.sn_main: sn,
    command.pd: pd,
    command.product_info_bms_main: product_info,
    command.bms_main: bms_main,
    command.product_info_inv: product_info,
    command.inv: inv,
    command.fan_auto: fan_auto,
    command.product_info_bms_extra: product_info,
    command.sn_extra: sn,
    command.bms_extra: bms_extra,
    (11, 1, 65): sn,
    (64, 1, 65): sn,
}
