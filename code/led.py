# from machine import Pin
from usr.logging import getLogger

log = getLogger(__name__)


class LED(object):
    def __init__(self, period=None):
        self.period = None

    def switch(self, flag=None):
        # TODO:
        # 1. flag is None Auto Check LED Status ON To OFF or OFF To ON.
        # 2. flag is 1 LED ON.
        # 3. flag is 0 LED OFF.
        pass
