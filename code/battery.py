
from misc import Power


class Battery(object):
    def __init__(self):
        pass

    def indicate(self, low_power_threshold, low_power_cb):
        self.low_power_threshold = low_power_threshold
        self.low_power_cb = low_power_cb
        pass

    def charge(self):
        pass

    def capacity(self):
        Vbatt = Power.getVbatt()
        # TODO: Get battery capacity from Vbatt
        battery_capacity = Vbatt
        return battery_capacity
