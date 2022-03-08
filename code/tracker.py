
from usr.location import Location
from usr.remote import Remote
# from usr.sensor import Sensor
# from usr.led import LED
from usr.alert import AlertMonitor


class Tracker():
    def __init__(self, loc_read_cb, alert_read_cb, **kw):
        self.remote = Remote()
        self.locator = Location(loc_read_cb)
        # self.sensor = Sensor()
        # self.led = LED()
        self.alert = AlertMonitor(alert_read_cb)
