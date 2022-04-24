product_info_pd = (2, 1, 5)
sn_main = (2, 1, 65)
pd = (2, 32, 2)
product_info_bms_main = (3, 1, 5)
bms_main = (3, 32, 2)
product_info_inv = (4, 1, 5)
inv = (4, 32, 2)
fan_auto = (4, 32, 74)
product_info_bms_extra = (6, 1, 5)
sn_extra = (6, 1, 65)
bms_extra = (6, 32, 2)


def dc_in_mode(product: int):
    if 12 < product < 16:
        return (5, 32, 82)
    else:
        return (4, 32, 68)
