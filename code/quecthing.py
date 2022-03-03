
import quecIot
from usr.logging import getLogger

DATA_NON_LOCA = 0x0
DATA_LOCA_NON_GPS = 0x1
DATA_LOCA_GPS = 0x2

log = getLogger('QuecThing')

class QuecThing(object):
    def __init__(self, pk, ps, downlink_queue):
        self.downlink_queue = downlink_queue
        quecIot.init()
        quecIot.setEventCB(self.eventCB)
        quecIot.setProductinfo(pk, ps)
        quecIot.setServer(1, "iot-south.quectel.com:2883")
        quecIot.setConnmode(1)

    def post_data(self, data_type, data):
        if data_type == DATA_NON_LOCA:
            quecIot.passTransSend(1, data)
        elif data_type == DATA_LOCA_GPS:
            quecIot.locReportOutside(data)
        elif data_type == DATA_LOCA_NON_GPS:
            quecIot.locReportInside(data)
        else:
            raise ValueError('No such locator (0x%X).' % data_type)

    def eventCB(self, data):
        log.info("event:", data)
        event = data[0]
        errcode = data[1]
        if len(data) > 2:
            data = data[2]

        if event == 1:
            if errcode == 10200:
                log.info('Device authentication succeeded.')
            elif errcode == 10422:
                log.info('Device has been authenticated (connect failed).')
        elif event == 2:
            if errcode == 10200:
                log.info('Access succeeded.')
        elif event == 3:
            if errcode == 10200:
                log.info('Subscription succeeded.')
        elif event == 4:
            if errcode == 10200:
                log.info('Data sending succeeded.')
            elif errcode == 10210:
                log.info('Object model data sending succeeded.')
            elif errcode == 10220:
                log.info('Location data sending succeeded.')
            elif errcode == 10300:
                log.info('Data sending failed.')
            elif errcode == 10310:
                log.info('Object model data sending failed.')
            elif errcode == 10320:
                log.info('Location data sending failed.')
        elif event == 5:
            if errcode == 10200:
                log.info('Recving raw data.')
                log.info(data)
                '''
                self.downlink_queue.put(data)
                '''
            if errcode == 10210:
                log.info('Recving object model data.')
                '''
                self.downlink_queue.put(data)
                '''
            elif errcode == 10211:
                log.info('Recving object model query command.')
        elif event == 6:
            if errcode == 10200:
                log.info('Logout succeeded.')
        elif event == 7:
            if errcode == 10700:
                log.info('New OTA plain.')
