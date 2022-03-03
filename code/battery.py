
class Battery(object):
    def __init__(self):
        pass

    def indicate(self, low_power_threshold, low_power_cb):
        self.low_power_threshold = low_power_threshold
        self.low_power_cb = low_power_cb
        pass

    def charge(self):
        pass