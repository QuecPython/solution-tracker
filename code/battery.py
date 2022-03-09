
from misc import Power

battery_ocv_table = {
    'nix_coy_mnzo2': {
        55: {
            4152: 100, 4083: 95, 4023: 90, 3967: 85, 3915: 80, 3864: 75, 3816: 70, 3773: 65, 3737: 60, 3685: 55,
            3656: 50, 3638: 45, 3625: 40, 3612: 35, 3596: 30, 3564: 25, 3534: 20, 3492: 15, 3457: 10, 3410: 5, 3380: 0,
        },
        20: {
            4143: 100, 4079: 95, 4023: 90, 3972: 85, 3923: 80, 3876: 75, 3831: 70, 3790: 65, 3754: 60, 3720: 55,
            3680: 50, 3652: 45, 3634: 40, 3621: 35, 3608: 30, 3595: 25, 3579: 20, 3548: 15, 3511: 10, 3468: 5, 3430: 0,
        },
        0: {
            4147: 100, 4089: 95, 4038: 90, 3990: 85, 3944: 80, 3899: 75, 3853: 70, 3811: 65, 3774: 60, 3741: 55,
            3708: 50, 3675: 45, 3651: 40, 3633: 35, 3620: 30, 3608: 25, 3597: 20, 3585: 15, 3571: 10, 3550: 5, 3500: 0,
        },
    },
}


def _get_soc_from_dict(key, volt_arg):
    if key in battery_ocv_table['nix_coy_mnzo2']:
        volts = sorted(battery_ocv_table['nix_coy_mnzo2'][key].keys(), reverse=True)
        pre_volt = 0
        volt_not_under = 0  # 判断电压是否低于soc最低电压值
        for volt in volts:
            if volt_arg > volt:
                volt_not_under = 1
                soc1 = battery_ocv_table['nix_coy_mnzo2'][key].get(volt, 0)
                soc2 = battery_ocv_table['nix_coy_mnzo2'][key].get(pre_volt, 0)
                break
            else:
                pre_volt = volt
        if pre_volt == 0:  # 电压高于最高电压soc
            return soc1
        elif volt_not_under == 0:
            return 0
        else:
            return soc2 - (soc2 - soc1) * (pre_volt - volt_arg) // (pre_volt - volt)


def get_soc(temp, volt_arg, bat_type='nix_coy_mnzo2'):
    if bat_type == 'nix_coy_mnzo2':
        if temp > 30:
            return _get_soc_from_dict(55, volt_arg)
        elif temp < 10:
            return _get_soc_from_dict(0, volt_arg)
        else:
            return _get_soc_from_dict(20, volt_arg)


class Battery(object):
    def __init__(self):
        pass

    def indicate(self, low_power_threshold, low_power_cb):
        self.low_power_threshold = low_power_threshold
        self.low_power_cb = low_power_cb
        pass

    def charge(self):
        pass

    def energy(self):
        volt_arg = Power.getVbatt()
        # TODO: Get temp from sensor
        temp = 20
        battery_energy = get_soc(temp, volt_arg)
        return battery_energy
