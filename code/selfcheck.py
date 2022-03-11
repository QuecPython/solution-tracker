
'''
check if network, gps, and all the sensors work normally
'''

import sim
import net
import utime
import usr.settings as settings
from usr.location import GPS


def net_check():
    # return True if OK
    if sim.getStatus() == 1:
        if net.getModemFun() == 1:
            return True

    return False


def gps_check():
    # return True if OK
    gps = GPS(settings.default_values_sys._gps_cfg)

    retry = 0
    gps_data = None
    sleep_time = 1
    while retry < 5:
        gps_data = gps.read()
        if gps_data:
            break
        else:
            retry += 1
            utime.sleep(sleep_time)
            sleep_time *= 2
    if gps_data:
        return True

    return False


def sensor_check():
    # return True if OK
    # TODO: How To Check Light & Movement Sensor?
    return True
