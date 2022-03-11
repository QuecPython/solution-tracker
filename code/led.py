from machine import Timer

import usr.settings as settings

# from machine import Pin
from usr.common import Singleton
from usr.logging import getLogger

log = getLogger(__name__)


class LED(Singleton):
    def __init__(self):
        current_settings = settings.settings.get()
        self.energy_led_timer = Timer(current_settings['sys']['energy_led_timern'])
        self.operating_led_timer = Timer(current_settings['sys']['operating_led_timern'])
        self.on_color = [None, None, None]
        self.on_period = [None, None, None]
        self.long_bright = False
        self.led_type = None

        # TODO: Three LED
        self.energy_led = None
        self.operating_led = None
        self.third_led = None

    def on(self, led_type):
        if led_type == 'energy_led':
            # color = self.on_color[0]
            pass
        elif led_type == 'operating_led':
            pass
        elif led_type == 'third_led':
            pass

    def off(self, led_type):
        if led_type == 'energy_led':
            pass
        elif led_type == 'operating_led':
            pass
        elif led_type == 'third_led':
            pass

    def led_timer_cb(self, args):
        if self.on_color:
            self.on(self.led_type)
        if self.long_bright is False:
            self.off(self.led_type)

    def flashing_mode(self, led_type, period, color=None):
        self.led_type = led_type
        self.long_bright = True if period == 0 else False
        if period == 0:
            mode = self.energy_led_timer.ONE_SHOT
        else:
            mode = self.energy_led_timer.PERIODIC

        if led_type == 'energy_led':
            if self.on_color[0] != color or self.on_period[0] != period:
                self.on_color[0] = color
                self.on_period[0] = period
                self.energy_led_timer.stop()
                self.energy_led_timer.start(period=period, mode=mode, callback=self.led_timer_cb)
        elif led_type == 'operating_led':
            if self.on_color[1] != color or self.on_period[1] != period:
                self.on_color[1] = color
                self.on_period[1] = period
                self.operating_led_timer.stop()
                self.operating_led_timer.start(period=period, mode=mode, callback=self.led_timer_cb)
        elif led_type == 'third_led':
            if self.on_color[2] != color or self.on_period[2] != period:
                self.on_color[2] = color
                self.on_period[2] = period
                pass
