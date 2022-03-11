# from machine import Pin
from usr.logging import getLogger

log = getLogger(__name__)


class LED(object):
    def __init__(self, period=None):
        self.period = None
        self.led_status = None

    def switch(self, flag=None):
        # TODO:
        # 1. flag is None Auto Check LED Status ON To OFF or OFF To ON.
        # 2. flag is 1 LED ON.
        # 3. flag is 0 LED OFF.
        if flag is None:
            if self.led_status == 1:
                self.led_status = 0
                # log.debug('LED SET OFF')
            else:
                self.led_status = 1
                # log.debug('LED SET ON')
        elif flag == 0:
            if self.led_status == 0:
                # log.debug('LED ALREADY OFF')
                pass
            else:
                self.led_status = 0
                # log.debug('LED SET OFF')
        elif flag == 1:
            if self.led_status == 1:
                # log.debug('LED ALREADY ON')
                pass
            else:
                self.led_status = 1
                # log.debug('LED SET ON')
        pass
