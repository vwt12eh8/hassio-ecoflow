PRODUCTS = {
    5: "RIVER",
    7: "RIVER 600 Pro",
    12: "RIVER Pro",
    13: "DELTA Max",
    14: "DELTA Pro",
    15: "DELTA Mini",
    17: "RIVER Mini",
    18: "RIVER Plus",
    20: "Smart Generator",
}


def has_extra(product: int, model: int):
    if product in [5, 12]:
        return model == 2


def has_light(product: int):
    return product in [5, 7, 12, 18]


def parse_cmd(data: bytes):
    if len(data) < 18:
        return
    if data[0] != 0xAA:
        return
    if data[1] != 2:
        # TODO
        return
    args = data[16:16 + int.from_bytes(data[2:4], "little")]
    if data[8] != 0:
        args = bytes(v ^ data[6] for v in args)

    return ((data[12], data[14], data[15]), args)
