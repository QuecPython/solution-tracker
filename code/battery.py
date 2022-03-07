
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

    def energy(self):
        Vbatt = Power.getVbatt()
        # TODO: Get battery energy from Vbatt
        battery_energy = Vbatt
        return battery_energy

    def power_status(self):
        return True

    def power_up(self):
        pass

    def power_down(self):
        # TODO: Send model info to cloud before power down.
        Power.powerDown()

    def power_restart(self):
        # TODO: Send model info to cloud before power restart.
        Power.powerRestart()
