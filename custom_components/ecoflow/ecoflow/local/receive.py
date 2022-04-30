from typing import Callable, Iterable, TypedDict

from . import command


def _parse_dict(d: bytes, types: Iterable[tuple[str, int, Callable]]):
    res = {}
    idx = 0
    for (name, size, fn) in types:
        if name is not None:
            res[name] = fn(d[idx:idx + size])
        idx += size
    return res


def _to_int(d: bytes):
    return int.from_bytes(d, "little")


def _to_utf8(d: bytes):
    return d.decode("utf-8")


def _to_ver(data):
    return ".".join(str(i) for i in data)


def _to_ver_reversed(data):
    return _to_ver(reversed(data))


def bms_main(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return bms_main_river(d)
    if 12 < product < 16:
        return bms_main_delta(d)
    if product == 17:
        return bms_main_river_mini(d)


def bms_main_delta(d: bytes):
    return _parse_dict(d, [
        ("chg_state", 1, _to_int),
        ("chg_cmd", 1, _to_int),
        ("dsg_cmd", 1, _to_int),
        ("chg_vol", 4, _to_int),
        ("chg_amp", 4, _to_int),
        ("fan_level", 1, _to_int),
        ("max_chg_soc", 1, _to_int),
        ("model", 1, _to_int),
        ("soc", 1, _to_int),
        ("open_ups_flag", 1, _to_int),
        ("warning", 1, _to_int),
        ("chg_remain_time", 4, _to_int),
        ("dsg_remain_time", 4, _to_int),
        ("is_normal_flag", 1, _to_int),
        ("soc_f32", 4, _to_int),
        ("is_connect", 3, _to_int),
        ("max_available_num", 1, _to_int),
        ("open_bms_idx", 1, _to_int),
        ("para_vol_min", 4, _to_int),
        ("para_vol_max", 4, _to_int),
        ("min_dsg_soc", 1, _to_int),
        ("open_oil_eb_soc", 1, _to_int),
        ("close_oil_eb_soc", 1, _to_int),
    ])


def bms_main_river(d: bytes):
    return _parse_dict(d, [
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("soc", 1, _to_int),
        ("vol", 4, _to_int),
        ("amp", 4, _to_int),
        ("temp", 1, _to_int),
        ("open_bms_idx", 1, _to_int),
        ("remain_cap", 4, _to_int),
        ("full_cap", 4, _to_int),
        ("cycles", 4, _to_int),
        ("max_chg_soc", 1, _to_int),
        ("max_cell_vol", 2, _to_int),
        ("min_cell_vol", 2, _to_int),
        ("max_cell_temp", 1, _to_int),
        ("min_cell_temp", 1, _to_int),
        ("max_mos_temp", 1, _to_int),
        ("min_mos_temp", 1, _to_int),
        ("fault", 1, _to_int),
        ("bq_sys_stat_reg", 1, _to_int),
        ("tag_chg_amp", 4, _to_int),
    ])


def bms_main_river_mini(d: bytes):
    # TODO
    return {}


def bms_extra(d: bytes, product: int):
    if product in [5, 7, 12, 18]:
        return bms_extra_river(d)
    if 12 < product < 16:
        return bms_extra_delta(d)


def bms_extra_river(d: bytes):
    return _parse_dict(d, [
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("soc", 1, _to_int),
        ("vol", 4, _to_int),
        ("amp", 4, _to_int),
        ("temp", 1, _to_int),
        ("remain_cap", 4, _to_int),
        ("full_cap", 4, _to_int),
        ("cycles", 4, _to_int),
        ("ambient_light_mode", 1, _to_int),
        ("ambient_light_animate", 1, _to_int),
        ("ambient_light_color", 4, list),
        ("ambient_light_brightness", 1, _to_int),
    ])


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
    return _parse_dict(d, [
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("chg_type", 1, _to_int),
        ("in_watts", 2, _to_int),
        ("ac_out_watts", 2, _to_int),
        ("inv_type", 1, _to_int),
        ("ac_out_vol", 4, _to_int),
        ("ac_out_amp", 4, _to_int),
        ("ac_out_freq", 1, _to_int),
        ("ac_in_vol", 4, _to_int),
        ("ac_in_amp", 4, _to_int),
        ("ac_in_freq", 1, _to_int),
        ("ac_out_temp", 1, _to_int),
        ("dc_in_vol", 4, _to_int),
        ("dc_in_amp", 4, _to_int),
        ("ac_in_temp", 1, _to_int),
        ("fan_state", 1, _to_int),
        ("ac_out", 1, _to_int),
        ("xboost", 1, _to_int),
        ("cfg_ac_out_vol", 4, _to_int),
        ("cfg_ac_out_freq", 1, _to_int),
        ("silence_charge", 1, _to_int),
        ("cfg_pause_flag", 1, _to_int),
        ("ac_dipsw", 1, _to_int),
        ("cfg_fast_chg_watts", 2, _to_int),
        ("cfg_slow_chg_watts", 2, _to_int),
    ])


def inv_river(d: bytes):
    return _parse_dict(d, [
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("chg_type", 1, _to_int),
        ("in_watts", 2, _to_int),
        ("ac_out_watts", 2, _to_int),
        ("inv_type", 1, _to_int),
        ("ac_out_vol", 4, _to_int),
        ("ac_out_amp", 4, _to_int),
        ("ac_out_freq", 1, _to_int),
        ("ac_in_vol", 4, _to_int),
        ("ac_in_amp", 4, _to_int),
        ("ac_in_freq", 1, _to_int),
        ("ac_out_temp", 1, _to_int),
        ("dc_in_vol", 4, _to_int),
        ("dc_in_amp", 4, _to_int),
        ("ac_in_temp", 1, _to_int),
        ("fan_state", 1, _to_int),
        ("ac_out", 1, _to_int),
        ("xboost", 1, _to_int),
        ("cfg_ac_out_vol", 4, _to_int),
        ("cfg_ac_out_freq", 1, _to_int),
        ("silence_charge", 1, _to_int),
    ])


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
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("wifi_ver", 4, _to_ver_reversed),
        ("wifi_auto_recovery", 1, _to_int),
        ("soc_sum", 1, _to_int),
        ("watts_out_sum", 2, _to_int),
        ("watts_in_sum", 2, _to_int),
        ("remain_time", 4, _to_int),
        ("beep", 1, _to_int),
        ("anderson_out", 1, _to_int),
        ("usb1_watts", 1, _to_int),
        ("usb2_watts", 1, _to_int),
        ("usbqc1_watts", 1, _to_int),
        ("usbqc2_watts", 1, _to_int),
        ("typec1_watts", 1, _to_int),
        ("typec2_watts", 1, _to_int),
        ("typec1_temp", 1, _to_int),
        ("typec2_temp", 1, _to_int),
        ("dc_out", 1, _to_int),
        ("dc_out_watts", 1, _to_int),
        ("dc_out_temp", 1, _to_int),
        ("standby_min", 2, _to_int),
        ("lcd_sec", 2, _to_int),
        ("lcd_brightness", 1, _to_int),
        ("chg_power_dc", 4, _to_int),
        ("chg_power_mppt", 4, _to_int),
        ("chg_power_ac", 4, _to_int),
        ("dsg_power_dc", 4, _to_int),
        ("dsg_power_ac", 4, _to_int),
        ("usb_used_time", 4, _to_int),
        ("typec_used_time", 4, _to_int),
        ("dc_out_used_time", 4, _to_int),
        ("ac_out_used_time", 4, _to_int),
        ("dc_in_used_time", 4, _to_int),
        ("mppt_used_time", 4, _to_int),
        (None, 8, None),
        ("sys_chg_flag", 1, _to_int),
    ])


def pd_river(d: bytes):
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("soc_sum", 1, _to_int),
        ("watts_out_sum", 2, _to_int),
        ("watts_in_sum", 2, _to_int),
        ("remain_time", 4, _to_int),
        ("dc_out", 1, _to_int),
        ("light_state", 1, _to_int),
        ("beep", 1, _to_int),
        ("typec1_watts", 1, _to_int),
        ("usb1_watts", 1, _to_int),
        ("usb2_watts", 1, _to_int),
        ("usbqc1_watts", 1, _to_int),
        ("dc_out_watts", 1, _to_int),
        ("led_watts", 1, _to_int),
        ("typec1_temp", 1, _to_int),
        ("dc_out_temp", 1, _to_int),
        ("standby_min", 2, _to_int),
        ("chg_power_dc", 4, _to_int),
        ("chg_power_mppt", 4, _to_int),
        ("chg_power_ac", 4, _to_int),
        ("dsg_power_dc", 4, _to_int),
        ("dsg_power_ac", 4, _to_int),
        ("usb_used_time", 4, _to_int),
        ("usbqc_used_time", 4, _to_int),
        ("typec_used_time", 4, _to_int),
        ("dc_out_used_time", 4, _to_int),
        ("ac_out_used_time", 4, _to_int),
        ("dc_in_used_time", 4, _to_int),
        ("mppt_used_time", 4, _to_int),
    ])


def pd_river_mini(d: bytes):
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("error_code", 4, _to_int),
        ("sys_ver", 4, _to_ver_reversed),
        ("wifi_ver", 4, _to_ver_reversed),
        ("wifi_auto_recovery", 1,),
        ("soc_sum", 1, _to_int),
        ("watts_out_sum", 2, _to_int),
        ("watts_in_sum", 2, _to_int),
        ("remain_time", 4, _to_int),
        ("beep", 1, _to_int),
        ("dc_out", 1, _to_int),
        ("usb1_watts", 1, _to_int),
        ("usb2_watts", 1, _to_int),
        ("usbqc1_watts", 1, _to_int),
        ("usbqc2_watts", 1, _to_int),
        ("typec1_watts", 1, _to_int),
        ("typec2_watts", 1, _to_int),
        ("typec1_temp", 1, _to_int),
        ("typec2_temp", 1, _to_int),
        ("dc_out_watts", 1, _to_int),
        ("dc_out_temp", 1, _to_int),
        ("standby_min", 2, _to_int),
        ("lcd_sec", 2, _to_int),
        ("lcd_brightness", 1, _to_int),
        ("chg_power_dc", 4, _to_int),
        ("chg_power_mppt", 4, _to_int),
        ("chg_power_ac", 4, _to_int),
        ("dsg_power_dc", 4, _to_int),
        ("dsg_power_ac", 4, _to_int),
        ("usb_used_time", 4, _to_int),
        ("usbqc_used_time", 4, _to_int),
        ("typec_used_time", 4, _to_int),
        ("dc_out_used_time", 4, _to_int),
        ("ac_out_used_time", 4, _to_int),
        ("dc_in_used_time", 4, _to_int),
        ("mppt_used_time", 4, _to_int),
        (None, 5, None),
        ("sys_chg_flag", 1, _to_int),
        ("wifi_rssi", 1, _to_int),
        ("wifi_watts", 1, _to_int),
    ])


def product_info(d: bytes, product: int = None):
    return _parse_dict(d, [
        ("product", 2, _to_int),
        ("product_detail", 2, _to_int),
        ("app_ver", 4, _to_ver),
        ("loader_ver", 4, _to_ver),
    ])


class Sn(TypedDict):
    chk_val: int
    product: int
    product_detail: int
    model: int
    serial: str
    cpu_id: str


def sn(d: bytes, product: int = None):
    return Sn(**_parse_dict(d, [
        ("chk_val", 4, _to_int),
        ("product", 1, _to_int),
        (None, 1, None),
        ("product_detail", 1, _to_int),
        ("model", 1, _to_int),
        ("serial", 15, _to_utf8),
        (None, 1, None),
        ("cpu_id", 12, _to_utf8),
    ]))


def dc_in_current(d: bytes, product: int = None):
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
