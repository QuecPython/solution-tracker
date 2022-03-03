
from usr.location import Location
from usr.location import Remote
from usr.sensor import Sensor
from usr.led import LED

class Tracker():
    def __init__(self, loc_read_cb, **kw):
        self.locator = Location(loc_read_cb, **kw)
        self.remote = Remote()
        self.sensor = Sensor()
        self.led = LED()
