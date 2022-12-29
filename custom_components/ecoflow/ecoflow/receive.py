from __future__ import annotations

import struct
from datetime import timedelta
from typing import Any, Callable, Iterable, TypedDict, cast

from reactivex import Observable, Observer

from . import calcCrc8, calcCrc16, is_delta, is_river, is_river_mini


class Serial(TypedDict):
    chk_val: int
    product: int
    product_detail: int
    model: int
    serial: str
    cpu_id: str


def _merge_packet(obs: Observable[bytes | None]):
    def func(sub: Observer[bytes], sched=None):
        x = b''

        def next(rcv: bytes | None):
            nonlocal x
            if rcv is None:
                x = b''
                return
            x += rcv
            while len(x) >= 18:
                if x[:2] != b'\xaa\x02':
                    x = x[1:]
                    continue
                size = int.from_bytes(x[2:4], 'little')
                if 18 + size > len(x):
                    return
                if calcCrc8(x[:4]) != x[4:5]:
                    x = x[2:]
                    continue
                if calcCrc16(x[:16 + size]) != x[16 + size:18 + size]:
                    x = x[2:]
                    continue
                sub.on_next(x[:18 + size])
                x = x[18 + size:]

        return obs.subscribe(next, sub.on_error, sub.on_completed, scheduler=sched)

    return Observable[bytes](func)


def _parse_dict(d: bytes, types: Iterable[tuple[str, int, Callable[[bytes], Any]]]):
    res = dict[str, Any]()
    idx = 0
    _len = len(d)
    for (name, size, fn) in types:
        if name is not None:
            res[name] = fn(d[idx:idx + size])
        idx += size
        if idx >= _len:
            break
    return res


def _to_float(d: bytes) -> float:
    return struct.unpack("<f", d)[0]


def _to_int(d: bytes):
    return int.from_bytes(d, "little")

def _to_hex_debug(d: bytes):
    return " ".join("0x{:02x}".format(x) for x in d)

def _to_int_ex(div: int = 1):
    def f(d: bytes):
        v = _to_int(d)
        if v is None:
            return None
        v /= div
        return v
    return f


def _to_timedelta_min(d: bytes):
    return timedelta(minutes=int.from_bytes(d, "little"))


def _to_timedelta_sec(d: bytes):
    return timedelta(seconds=int.from_bytes(d, "little"))


def _to_utf8(d: bytes):
    try:
        return d.decode("utf-8")
    except:
        return None


def _to_ver(data: Iterable[int]):
    return ".".join(str(i) for i in data)


def _to_ver_reversed(data: Iterable[int]):
    return _to_ver(reversed(data))


def decode_packet(x: bytes):
    size = int.from_bytes(x[2:4], 'little')
    args = x[16:16 + size]
    if ((x[5] >> 5) & 3) == 1:
        # Deobfuscation
        args = bytes(v ^ x[6] for v in args)
    return (x[12], x[14], x[15], args)


def is_bms(x: tuple[int, int, int]):
    return x[0:3] == (3, 32, 50) or x[0:3] == (6, 32, 2) or x[0:3] == (6, 32, 50)


def is_dc_in_current_config(x: tuple[int, int, int]):
    return x[0:3] == (4, 32, 72) or x[0:3] == (5, 32, 72)


def is_dc_in_type(x: tuple[int, int, int]):
    return x[0:3] == (4, 32, 68) or x[0:3] == (5, 32, 82)


def is_ems(x: tuple[int, int, int]):
    return x[0:3] == (3, 32, 2)


def is_fan_auto(x: tuple[int, int, int]):
    return x[0:3] == (4, 32, 74)


def is_inverter(x: tuple[int, int, int]):
    return x[0:3] == (4, 32, 2)


def is_lcd_timeout(x: tuple[int, int, int]):
    return x[0:3] == (2, 32, 40)


def is_mppt(x: tuple[int, int, int]):
    return x[0:3] == (5, 32, 2)


def is_pd(x: tuple[int, int, int]):
    return x[0:3] == (2, 32, 2)


def is_serial_main(x: tuple[int, int, int]):
    return x[0] in [2, 11] and x[1:3] == (1, 65)


def is_serial_extra(x: tuple[int, int, int]):
    return x[0:3] == (6, 1, 65)


def parse_bms(d: bytes, product: int):
    if is_delta(product):
        return parse_bms_delta(d)
    if is_river(product):
        return parse_bms_river(d)
    return (0, {})


def parse_bms_delta(d: bytes):
    val = _parse_dict(d, [
        ("num", 1, _to_int),
        ("battery_type", 1, _to_int),
        ("battery_cell_id", 1, _to_int),
        ("battery_error", 4, _to_int),
        ("battery_version", 4, _to_ver_reversed),
        ("battery_level", 1, _to_int),
        ("battery_voltage", 4, _to_int_ex(div=1000)),
        ("battery_current", 4, _to_int),
        ("battery_temp", 1, _to_int),
        ("_open_bms_idx", 1, _to_int),
        ("battery_capacity_design", 4, _to_int),
        ("battery_capacity_remain", 4, _to_int),
        ("battery_capacity_full", 4, _to_int),
        ("battery_cycles", 4, _to_int),
        ("_soh", 1, _to_int),
        ("battery_voltage_max", 2, _to_int_ex(div=1000)),
        ("battery_voltage_min", 2, _to_int_ex(div=1000)),
        ("battery_temp_max", 1, _to_int),
        ("battery_temp_min", 1, _to_int),
        ("battery_mos_temp_max", 1, _to_int),
        ("battery_mos_temp_min", 1, _to_int),
        ("battery_fault", 1, _to_int),
        ("_sys_stat_reg", 1, _to_int),
        ("_tag_chg_current", 4, _to_int),
        ("battery_level_f32", 4, _to_float),
        ("battery_in_power", 4, _to_int),
        ("battery_out_power", 4, _to_int),
        ("battery_remain", 4, _to_timedelta_min),
    ])
    return (cast(int, val.pop("num")), val)


def parse_bms_river(d: bytes):
    return (1, _parse_dict(d, [
        ("battery_error", 4, _to_int),
        ("battery_version", 4, _to_ver_reversed),
        ("battery_level", 1, _to_int),
        ("battery_voltage", 4, _to_int_ex(div=1000)),
        ("battery_current", 4, _to_int),
        ("battery_temp", 1, _to_int),
        ("battery_capacity_remain", 4, _to_int),
        ("battery_capacity_full", 4, _to_int),
        ("battery_cycles", 4, _to_int),
        ("ambient_mode", 1, _to_int),
        ("ambient_animate", 1, _to_int),
        ("ambient_color", 4, list),
        ("ambient_brightness", 1, _to_int),
    ]))


def parse_dc_in_current_config(d: bytes):
    return int.from_bytes(d[:4], "little")


def parse_dc_in_type(d: bytes):
    return d[1]


def parse_ems(d: bytes, product: int):
    if is_delta(product):
        return parse_ems_delta(d)
    if is_river(product):
        return parse_ems_river(d)
    # if is_river_mini(product):
    #     return parse_ems_river_mini(d)
    return {}


def parse_ems_delta(d: bytes):
    return _parse_dict(d, [
        ("_state_charge", 1, _to_int),
        ("_chg_cmd", 1, _to_int),
        ("_dsg_cmd", 1, _to_int),
        ("battery_main_voltage", 4, _to_int_ex(div=1000)),
        ("battery_main_current", 4, _to_int_ex(div=1000)),
        ("_fan_level", 1, _to_int),
        ("battery_level_max", 1, _to_int),
        ("model", 1, _to_int),
        ("battery_main_level", 1, _to_int),
        ("_flag_open_ups", 1, _to_int),
        ("battery_main_warning", 1, _to_int),
        ("battery_remain_charge", 4, _to_timedelta_min),
        ("battery_remain_discharge", 4, _to_timedelta_min),
        ("battery_main_normal", 1, _to_int),
        ("battery_main_level_f32", 4, _to_float),
        ("_is_connect", 3, _to_int),
        ("_max_available_num", 1, _to_int),
        ("_open_bms_idx", 1, _to_int),
        ("battery_main_voltage_min", 4, _to_int_ex(div=1000)),
        ("battery_main_voltage_max", 4, _to_int_ex(div=1000)),
        ("battery_level_min", 1, _to_int),
        ("generator_level_start", 1, _to_int),
        ("generator_level_stop", 1, _to_int),
    ])


def parse_ems_river(d: bytes):
    return _parse_dict(d, [
        ("battery_main_error", 4, _to_int),
        ("battery_main_version", 4, _to_ver_reversed),
        ("battery_main_level", 1, _to_int),
        ("battery_main_voltage", 4, _to_int_ex(div=1000)),
        ("battery_main_current", 4, _to_int),
        ("battery_main_temp", 1, _to_int),
        ("_open_bms_idx", 1, _to_int),
        ("battery_capacity_remain", 4, _to_int),
        ("battery_capacity_full", 4, _to_int),
        ("battery_cycles", 4, _to_int),
        ("battery_level_max", 1, _to_int),
        ("battery_main_voltage_max", 2, _to_int_ex(div=1000)),
        ("battery_main_voltage_min", 2, _to_int_ex(div=1000)),
        ("battery_main_temp_max", 1, _to_int),
        ("battery_main_temp_min", 1, _to_int),
        ("mos_temp_max", 1, _to_int),
        ("mos_temp_min", 1, _to_int),
        ("battery_main_fault", 1, _to_int),
        ("_bq_sys_stat_reg", 1, _to_int),
        ("_tag_chg_amp", 4, _to_int),
    ])


# def parse_ems_river_mini(d: bytes):
#     pass

def parse_fan_auto(d: bytes):
    return d[0] == 1


def parse_inverter(d: bytes, product: int):
    if is_delta(product):
        return parse_inverter_delta(d)
    if is_river(product):
        return parse_inverter_river(d)
    if is_river_mini(product):
        return parse_inverter_river_mini(d)
    return {}


def parse_inverter_delta(d: bytes):
    return _parse_dict(d, [
        ("ac_error", 4, _to_int),
        ("ac_version", 4, _to_ver_reversed),
        ("ac_in_type", 1, _to_int),
        ("ac_in_power", 2, _to_int),
        ("ac_out_power", 2, _to_int),
        ("ac_type", 1, _to_int),
        ("ac_out_voltage", 4, _to_int_ex(div=1000)),
        ("ac_out_current", 4, _to_int_ex(div=1000)),
        ("ac_out_freq", 1, _to_int),
        ("ac_in_voltage", 4, _to_int_ex(div=1000)),
        ("ac_in_current", 4, _to_int_ex(div=1000)),
        ("ac_in_freq", 1, _to_int),
        ("ac_out_temp", 2, _to_int),
        ("dc_in_voltage", 4, _to_int),
        ("dc_in_current", 4, _to_int),
        ("ac_in_temp", 2, _to_int),
        ("fan_state", 1, _to_int),
        ("ac_out_state", 1, _to_int),
        ("ac_out_xboost", 1, _to_int),
        ("ac_out_voltage_config", 4, _to_int_ex(div=1000)),
        ("ac_out_freq_config", 1, _to_int),
        ("fan_config", 1, _to_int),
        ("ac_in_pause", 1, _to_int),
        ("ac_in_limit_switch", 1, _to_int),
        ("ac_in_limit_max", 2, _to_int),
        ("ac_in_limit_custom", 2, _to_int),
        ("ac_out_timeout", 2, _to_int),
    ])


def parse_inverter_river(d: bytes):
    return _parse_dict(d, [
        ("ac_error", 4, _to_int),
        ("ac_version", 4, _to_ver_reversed),
        ("in_type", 1, _to_int),
        ("in_power", 2, _to_int),
        ("ac_out_power", 2, _to_int),
        ("ac_type", 1, _to_int),
        ("ac_out_voltage", 4, _to_int_ex(div=1000)),
        ("ac_out_current", 4, _to_int_ex(div=1000)),
        ("ac_out_freq", 1, _to_int),
        ("ac_in_voltage", 4, _to_int_ex(div=1000)),
        ("ac_in_current", 4, _to_int_ex(div=1000)),
        ("ac_in_freq", 1, _to_int),
        ("ac_out_temp", 1, _to_int),
        ("dc_in_voltage", 4, _to_int_ex(div=1000)),
        ("dc_in_current", 4, _to_int_ex(div=1000)),
        ("ac_in_temp", 1, _to_int),
        ("fan_state", 1, _to_int),
        ("ac_out_state", 1, _to_int),
        ("ac_out_xboost", 1, _to_int),
        ("ac_out_voltage_config", 4, _to_int_ex(div=1000)),
        ("ac_out_freq_config", 1, _to_int),
        ("ac_in_slow", 1, _to_int),
        ("ac_out_timeout", 2, _to_int),
        ("fan_config", 1, _to_int),
    ])

def parse_inverter_river_mini(d: bytes):
    return _parse_dict(d, [
        ("ac_error", 4, _to_int),
        ("ac_version", 4, _to_ver_reversed),
        ("in_type", 1, _to_int),
        ("in_power", 2, _to_int),
        ("ac_out_power", 2, _to_int),
        ("ac_type", 1, _to_int),
        ("ac_out_voltage", 4, _to_int_ex(div=1000)),
        ("ac_out_current", 4, _to_int_ex(div=1000)),
        ("ac_out_freq", 1, _to_int),
        ("ac_in_voltage", 4, _to_int_ex(div=1000)),
        ("ac_in_current", 4, _to_int_ex(div=1000)),
        ("ac_in_freq", 1, _to_int),
        ("ac_out_temp", 1, _to_int),
        ("dc_in_voltage", 4, _to_int_ex(div=1000)),
        ("dc_in_current", 4, _to_int_ex(div=1000)),
        ("ac_in_temp", 1, _to_int),
        ("fan_state", 1, _to_int),
        ("ac_out_state", 1, _to_int),
        ("ac_out_xboost", 1, _to_int),
        ("ac_out_voltage_config", 4, _to_int_ex(div=1000)),
        ("ac_out_freq_config", 1, _to_int),
        ("ac_in_slow", 1, _to_int),
        ("battery_main_level", 1, _to_int),
        ("battery_main_voltage", 4, _to_int_ex(div=1000)),
        ("battery_current", 4, _to_int),
        ("battery_main_temp", 1, _to_int),
        ("_open_bms_idx", 1, _to_int),
        ("battery_capacity_remain", 4, _to_int),
        ("battery_capacity_full", 4, _to_int),
        ("battery_cycles", 4, _to_int),
        ("battery_level_max", 1, _to_int),
        ("battery_main_level_f32", 4, _to_float),
        ("ac_out_timeout", 2, _to_int),
    ])


def parse_lcd_timeout(d: bytes):
    return int.from_bytes(d[1:3], "little")


def parse_mppt(d: bytes, product: int):
    if is_delta(product):
        return parse_mppt_delta(d)
    return {}


def parse_mppt_delta(d: bytes):
    return _parse_dict(d, [
        ("dc_in_error", 4, _to_int),
        ("dc_in_version", 4, _to_ver_reversed),
        ("dc_in_voltage", 4, _to_int_ex(div=10)),
        ("dc_in_current", 4, _to_int_ex(div=100)),
        ("dc_in_power", 2, _to_int_ex(div=10)),
        ("_volt_?_out", 4, _to_int),
        ("_curr_?_out", 4, _to_int),
        ("_watts_?_out", 2, _to_int),
        ("dc_in_temp", 2, _to_int),
        ("dc_in_type", 1, _to_int),
        ("dc_in_type_config", 1, _to_int),
        ("_dc_in_type", 1, _to_int),
        ("dc_in_state", 1, _to_int),
        ("anderson_out_voltage", 4, _to_int),
        ("anderson_out_current", 4, _to_int),
        ("anderson_out_power", 2, _to_int),
        ("car_out_voltage", 4, _to_int_ex(div=10)),
        ("car_out_current", 4, _to_int_ex(div=100)),
        ("car_out_power", 2, _to_int_ex(div=10)),
        ("car_out_temp", 2, _to_int),
        ("car_out_state", 1, _to_int),
        ("dc24_temp", 2, _to_int),
        ("dc24_state", 1, _to_int),
        ("dc_in_pause", 1, _to_int),
        ("_dc_in_switch", 1, _to_int),
        ("_dc_in_limit_max", 2, _to_int),
        ("_dc_in_limit_custom", 2, _to_int),
    ])


def parse_pd(d: bytes, product: int):
    if is_delta(product):
        return parse_pd_delta(d)
    if is_river(product):
        return parse_pd_river(d)
    if is_river_mini(product):
        return parse_pd_river_mini(d)
    return {}


def parse_pd_delta(d: bytes):
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("pd_error", 4, _to_int),
        ("pd_version", 4, _to_ver_reversed),
        ("wifi_version", 4, _to_ver_reversed),
        ("wifi_autorecovery", 1, _to_int),
        ("battery_level", 1, _to_int),
        ("out_power", 2, _to_int),
        ("in_power", 2, _to_int),
        ("remain_display", 4, _to_timedelta_min),
        ("beep", 1, _to_int),
        ("_watts_anderson_out", 1, _to_int),
        ("usb_out1_power", 1, _to_int),
        ("usb_out2_power", 1, _to_int),
        ("usbqc_out1_power", 1, _to_int),
        ("usbqc_out2_power", 1, _to_int),
        ("typec_out1_power", 1, _to_int),
        ("typec_out2_power", 1, _to_int),
        ("typec_out1_temp", 1, _to_int),
        ("typec_out2_temp", 1, _to_int),
        ("car_out_state", 1, _to_int),
        ("car_out_power", 1, _to_int),
        ("car_out_temp", 1, _to_int),
        ("standby_timeout", 2, _to_int),
        ("lcd_timeout", 2, _to_int),
        ("lcd_brightness", 1, _to_int),
        ("car_in_energy", 4, _to_int),
        ("mppt_in_energy", 4, _to_int),
        ("ac_in_energy", 4, _to_int),
        ("dc_out_energy", 4, _to_int),
        ("ac_out_energy", 4, _to_int),
        ("usb_time", 4, _to_timedelta_sec),
        ("typec_time", 4, _to_timedelta_sec),
        ("car_out_time", 4, _to_timedelta_sec),
        ("ac_out_time", 4, _to_timedelta_sec),
        ("ac_in_time", 4, _to_timedelta_sec),
        ("car_in_time", 4, _to_timedelta_sec),
        ("mppt_time", 4, _to_timedelta_sec),
        (None, 2, None),
        ("_ext_rj45", 1, _to_int),
        ("_ext_infinity", 1, _to_int),
    ])


def parse_pd_river(d: bytes):
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("pd_error", 4, _to_int),
        ("pd_version", 4, _to_ver_reversed),
        ("battery_level", 1, _to_int),
        ("out_power", 2, _to_int),
        ("in_power", 2, _to_int),
        ("remain_display", 4, _to_timedelta_min),
        ("car_out_state", 1, _to_int),
        ("light_state", 1, _to_int),
        ("beep", 1, _to_int),
        ("typec_out1_power", 1, _to_int),
        ("usb_out1_power", 1, _to_int),
        ("usb_out2_power", 1, _to_int),
        ("usbqc_out1_power", 1, _to_int),
        ("car_out_power", 1, _to_int),
        ("light_power", 1, _to_int),
        ("typec_out1_temp", 1, _to_int),
        ("car_out_temp", 1, _to_int),
        ("standby_timeout", 2, _to_int),
        ("car_in_energy", 4, _to_int),
        ("mppt_in_energy", 4, _to_int),
        ("ac_in_energy", 4, _to_int),
        ("dc_out_energy", 4, _to_int),
        ("ac_out_energy", 4, _to_int),
        ("usb_time", 4, _to_timedelta_sec),
        ("usbqc_time", 4, _to_timedelta_sec),
        ("typec_time", 4, _to_timedelta_sec),
        ("car_out_time", 4, _to_timedelta_sec),
        ("ac_out_time", 4, _to_timedelta_sec),
        ("car_in_time", 4, _to_timedelta_sec),
        ("mppt_time", 4, _to_timedelta_sec),
    ])


def parse_pd_river_mini(d: bytes):
    return _parse_dict(d, [
        ("model", 1, _to_int),
        ("pd_error", 4, _to_int),
        ("pd_version", 4, _to_ver_reversed),
        ("wifi_version", 4, _to_ver_reversed),
        ("wifi_autorecovery", 1, _to_int),
        ("battery_level", 1, _to_int),
        ("out_power", 2, _to_int),
        ("in_power", 2, _to_int),
        ("remain_display", 4, _to_timedelta_min),
        ("beep", 1, _to_int),
        ("usb_out1_state", 1, _to_int),
        ("usb_out1_power", 1, _to_int),
        ("usb2_watts", 1, _to_int),
        ("usbqc1_watts", 1, _to_int),
        ("usbqc2_watts", 1, _to_int),
        ("typec1_watts", 1, _to_int),
        ("typec2_watts", 1, _to_int),
        ("typec1_temp", 1, _to_int),
        ("typec2_temp", 1, _to_int),
        ("car_out_state", 1, _to_int),
        ("car_out_power", 1, _to_int),
        ("car_out_temp", 1, _to_int),
        ("standby_timeout", 1, _to_int),
        ("unknown_1", 1, _to_hex_debug),
        ("lcd_timeout", 2, _to_int),
        ("lcd_brightness", 1, _to_int),
        ("car_in_energy", 4, _to_int),
        ("mppt_in_energy", 4, _to_int),
        ("ac_in_energy", 4, _to_int),
        ("dc_out_energy", 4, _to_int),
        ("ac_out_energy", 4, _to_int),
        ("usb_time", 4, _to_timedelta_sec),
        ("unknown_2", 8, _to_hex_debug),
        ("car_out_time", 4, _to_timedelta_sec),
        ("ac_out_time", 4, _to_timedelta_sec),
        ("car_in_time", 4, _to_timedelta_sec),
        ("mppt_time", 4, _to_timedelta_sec),
        ("unknown_3", 30, _to_hex_debug),
    ])


def parse_serial(d: bytes) -> Serial:
    return _parse_dict(d, [
        ("chk_val", 4, _to_int),
        ("product", 1, _to_int),
        (None, 1, None),
        ("product_detail", 1, _to_int),
        ("model", 1, _to_int),
        ("serial", 15, _to_utf8),
        (None, 1, None),
        ("cpu_id", 12, _to_utf8),
    ])


def merge_packet():
    return _merge_packet
