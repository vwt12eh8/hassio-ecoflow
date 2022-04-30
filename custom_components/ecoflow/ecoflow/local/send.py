from typing import Optional
from . import command

NO_USB_SWITCH = {5, 7, 12, 14, 15, 18}


_crc8_tab = [0, 7, 14, 9, 28, 27, 18, 21, 56, 63, 54, 49, 36, 35, 42, 45, 112, 119, 126, 121, 108, 107, 98, 101, 72, 79, 70, 65, 84, 83, 90, 93, 224, 231, 238, 233, 252, 251, 242, 245, 216, 223, 214, 209, 196, 195, 202, 205, 144, 151, 158, 153, 140, 139, 130, 133, 168, 175, 166, 161, 180, 179, 186, 189, 199, 192, 201, 206, 219, 220, 213, 210, 255, 248, 241, 246, 227, 228, 237, 234, 183, 176, 185, 190, 171, 172, 165, 162, 143, 136, 129, 134, 147, 148, 157, 154, 39, 32, 41, 46, 59, 60, 53, 50, 31, 24, 17, 22, 3, 4, 13, 10, 87, 80, 89, 94, 75, 76, 69, 66, 111, 104, 97, 102, 115, 116, 125,
             122, 137, 142, 135, 128, 149, 146, 155, 156, 177, 182, 191, 184, 173, 170, 163, 164, 249, 254, 247, 240, 229, 226, 235, 236, 193, 198, 207, 200, 221, 218, 211, 212, 105, 110, 103, 96, 117, 114, 123, 124, 81, 86, 95, 88, 77, 74, 67, 68, 25, 30, 23, 16, 5, 2, 11, 12, 33, 38, 47, 40, 61, 58, 51, 52, 78, 73, 64, 71, 82, 85, 92, 91, 118, 113, 120, 127, 106, 109, 100, 99, 62, 57, 48, 55, 34, 37, 44, 43, 6, 1, 8, 15, 26, 29, 20, 19, 174, 169, 160, 167, 178, 181, 188, 187, 150, 145, 152, 159, 138, 141, 132, 131, 222, 217, 208, 215, 194, 197, 204, 203, 230, 225, 232, 239, 250, 253, 244, 243]
_crc16_tab = [0, 49345, 49537, 320, 49921, 960, 640, 49729, 50689, 1728, 1920, 51009, 1280, 50625, 50305, 1088, 52225, 3264, 3456, 52545, 3840, 53185, 52865, 3648, 2560, 51905, 52097, 2880, 51457, 2496, 2176, 51265, 55297, 6336, 6528, 55617, 6912, 56257, 55937, 6720, 7680, 57025, 57217, 8000, 56577, 7616, 7296, 56385, 5120, 54465, 54657, 5440, 55041, 6080, 5760, 54849, 53761, 4800, 4992, 54081, 4352, 53697, 53377, 4160, 61441, 12480, 12672, 61761, 13056, 62401, 62081, 12864, 13824, 63169, 63361, 14144, 62721, 13760, 13440, 62529, 15360, 64705, 64897, 15680, 65281, 16320, 16000, 65089, 64001, 15040, 15232, 64321, 14592, 63937, 63617, 14400, 10240, 59585, 59777, 10560, 60161, 11200, 10880, 59969, 60929, 11968, 12160, 61249, 11520, 60865, 60545, 11328, 58369, 9408, 9600, 58689, 9984, 59329, 59009, 9792, 8704, 58049, 58241, 9024, 57601, 8640, 8320, 57409, 40961, 24768,
              24960, 41281, 25344, 41921, 41601, 25152, 26112, 42689, 42881, 26432, 42241, 26048, 25728, 42049, 27648, 44225, 44417, 27968, 44801, 28608, 28288, 44609, 43521, 27328, 27520, 43841, 26880, 43457, 43137, 26688, 30720, 47297, 47489, 31040, 47873, 31680, 31360, 47681, 48641, 32448, 32640, 48961, 32000, 48577, 48257, 31808, 46081, 29888, 30080, 46401, 30464, 47041, 46721, 30272, 29184, 45761, 45953, 29504, 45313, 29120, 28800, 45121, 20480, 37057, 37249, 20800, 37633, 21440, 21120, 37441, 38401, 22208, 22400, 38721, 21760, 38337, 38017, 21568, 39937, 23744, 23936, 40257, 24320, 40897, 40577, 24128, 23040, 39617, 39809, 23360, 39169, 22976, 22656, 38977, 34817, 18624, 18816, 35137, 19200, 35777, 35457, 19008, 19968, 36545, 36737, 20288, 36097, 19904, 19584, 35905, 17408, 33985, 34177, 17728, 34561, 18368, 18048, 34369, 33281, 17088, 17280, 33601, 16640, 33217, 32897, 16448]


def _btoi(b: Optional[bool]):
    if b is None:
        return 255
    return 1 if b else 0


def calcCrc8(data: bytes):
    crc = 0
    for i3 in range(len(data)):
        crc = _crc8_tab[(crc ^ data[i3]) & 255]
    return crc.to_bytes(1, "little")


def calcCrc16(data: bytes):
    crc = 0
    for i3 in range(len(data)):
        crc = _crc16_tab[(crc ^ data[i3]) & 255] ^ (crc >> 8)
    return crc.to_bytes(2, "little")


def build2(dst: int, cmd_set: int, cmd_id: int, data: bytes = b''):
    b = bytes([170, 2])
    b += len(data).to_bytes(2, "little")
    b += calcCrc8(b)
    b += bytes([0x0D, 0, 0, 0, 0, 0, 0, 32, dst, cmd_set, cmd_id])
    b += data
    b += calcCrc16(b)
    return b


def build3(dst: int, cmd_set: int, cmd_id: int, data: bytes = b''):
    b = bytes([170, 3])
    b += len(data).to_bytes(2, "little")
    b += calcCrc8(b)
    b += bytes([0x0D, 0, 0, 0, 0, 0, 0, 32, dst, 0, 0, cmd_set, cmd_id])
    b += data
    b += calcCrc16(b)
    return b


def get_product_info(dst: int):
    return build2(dst, 1, 5)


def get_cpu_id():
    return build2(2, 1, 64)


def get_sn_main():
    return build2(2, 1, 65)


def set_sn(value: str):
    return build2(2, 1, 66, value.encode() + b'\0')


def get_pd():
    return build2(*command.pd)


def reset():
    return build2(2, 32, 3)


def system_stand(value: int):
    return build2(2, 32, 33, value.to_bytes(2, "little"))


def set_usb(enable: bool):
    return build2(2, 32, 34, bytes([1 if enable else 0]))


def set_light(product: int, value: int):
    return build2(2, 32, 35, bytes([value]))


def set_dc_out(product: int, enable: bool):
    if 12 < product < 16:
        cmd = (5, 32, 81)
    elif product == 20:
        cmd = (8, 8, 3)
    elif product in [5, 7, 12, 18]:
        cmd = (2, 32, 34)
    else:
        cmd = (2, 32, 37)
    return build2(*cmd, bytes([1 if enable else 0]))


def set_buzzer(enable: bool):
    return build2(2, 32, 38, bytes([0 if enable else 1]))


def set_lcd(product: int, time: int = 0xFFFF, light: int = 255):
    arg = time.to_bytes(2, "little")
    if (12 < product < 16) or product == 17:
        arg += bytes([light])
    return build2(2, 32, 39, arg)


def close(value: int):
    return build2(2, 32, 41, value.to_bytes(2, "little"))


def get_bms_main():
    return build2(*command.bms_main)


def set_ups(product: int, value: int):
    dst = 4 if product == 17 else 3
    return build2(dst, 32, 49, bytes([value]))


def set_min_dsg(value: int):
    return build2(3, 32, 51, bytes([value]))


def open_oil(value: int):
    return build2(3, 32, 52, bytes([value]))


def close_oil(value: int):
    return build2(3, 32, 53, bytes([value]))


def get_inv():
    return build2(*command.inv)


def set_silence_charge(product: int, value: bool):
    return build2(4, 32, 65, bytes([_btoi(value)]))


def set_ac_out(product: int, enable: bool = None, xboost: bool = None, freq: int = 255):
    if product == 20:
        cmd = (8, 8, 2)
        arg = [_btoi(enable)]
    else:
        cmd = (4, 32, 66)
        arg = [_btoi(enable), _btoi(xboost), 255, 255, 255, 255, freq]
    return build2(*cmd, bytes(arg))


def set_dc_in_mode(product: int, value: int):
    if 12 < product < 16:
        cmd = (5, 32, 82)
    else:
        cmd = (4, 32, 67)
    return build2(*cmd, bytes([value]))


def get_dc_in_mode(product: int):
    cmd = command.dc_in_mode(product)
    return build2(*cmd, bytes([0]))


def set_sc_watts(value: int):
    arg = bytes([255, 255])
    arg += value.to_bytes(2, "little")
    arg += bytes([255])
    return build2(4, 32, 69, arg)


def set_chg_pause(value: int):
    return build2(4, 32, 69, bytes([255, 255, 255, 255, value]))


def set_dc_in_current(product: int, value: int):
    dst = 5 if 12 < product < 16 else 4
    return build2(dst, 32, 71, value.to_bytes(4, "little"))


def get_dc_in_current(product: int):
    dst = 5 if 12 < product < 16 else 4
    return build2(dst, 32, 72)


def set_fan_auto(product: int, value: bool):
    return build2(4, 32, 73, bytes([1 if value else 3]))


def get_fan_auto():
    return build2(4, 32, 74)


def get_lab():
    return build2(4, 32, 84)


def set_lab(value: int):
    return build2(4, 32, 84, bytes([value]))


def set_ac_standby_min(value: int):
    return build2(4, 32, 153, value.to_bytes(2, "little"))


def get_sn_extra():
    return build2(6, 1, 65)


def get_bms_extra():
    return build2(*command.bms_extra)


def set_ambient(model: int = 255, mode: int = 255, color=(255, 255, 255, 255), brightness=255):
    arg = [model, mode, *color, brightness]
    return build2(6, 32, 97, bytes(arg))


def set_watt(value: int):
    return build2(8, 8, 7, value.to_bytes(2, "little"))
