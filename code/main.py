
from usr.tracker import Tracker
from usr.settings import settings
from usr.settings import default_values_sys
from usr.logging import getLogger

log = getLogger(__name__)

PROJECT_NAME = 'QuecPython_Tracker'

PROJECT_VERSION = '2.0.0'


def main():
    log.info('PROJECT_NAME: %s' % PROJECT_NAME)
    log.info('PROJECT_VERSION: %s' % PROJECT_VERSION)
    current_settings = settings.get()

    tracker = Tracker()
    # Start Device Check
    tracker.device_check()

    # Start OTA Check
    if current_settings['sys']['cloud'] == default_values_sys._cloud.quecIot and \
            current_settings['app']['sw_ota'] is True:
        tracker.remote.check_ota()

    # Start PowerManage
    # Init Low Energy Work Mode
    tracker.power_manage.low_energy_init()
    # Start RTC
    tracker.power_manage.start_rtc()


if __name__ == '__main__':
    main()
