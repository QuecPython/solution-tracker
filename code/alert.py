
from usr import settings
from usr.logging import getLogger
from usr.common import Singleton

log = getLogger(__name__)


class AlertMonitor(Singleton):
    '''
    Recv alert signals and process them
    '''
    def __init__(self, alert_read_cb=None):
        self.alert_read_cb = alert_read_cb

    def post_alert(self, alert_code, alert_info):
        if settings.ALERTCODE.get(alert_code):
            current_settings = settings.settings.get()
            alert_status = current_settings.get('app', {}).get('sw_' + settings.ALERTCODE.get(alert_code))
            if alert_status:
                if self.alert_read_cb:
                    return self.alert_read_cb(settings.ALERTCODE.get(alert_code), alert_info)
                else:
                    log.warn('Alert callback is not defined.')
            else:
                log.warn('%s status is %s' % (settings.ALERTCODE.get(alert_code), alert_status))
        else:
            log.error('altercode (%s) is not exists. alert info: %s' % (alert_code, alert_info))

        return False
