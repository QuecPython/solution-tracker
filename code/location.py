
import ure
import _thread
import cellLocator
from wifilocator import wifilocator
import usr.settings as settings

from queue import Queue
from machine import UART

gps_data_retrieve_queue = None


def gps_data_retrieve_cb(para_list):
    '''
    GPS data retrieve callback from UART
    When data comes, send a message to queue of data length
    '''
    global gps_data_retrieve_queue
    toRead = para_list[2]
    if toRead:
        gps_data_retrieve_queue.put(toRead)


def gps_data_retrieve_thread(argv):
    '''
    GPS data retrieve thread
    Receive a message from queue of data length.
    Then read the corresponding length of data from UART into self.gps_data.
    So self.gps_data will be updated immediately once the data comes to UART that
    the self.gps_data could keep the latest data.
    '''
    global gps_data_retrieve_queue
    self = argv

    while True:
        toRead = gps_data_retrieve_queue.get()
        if toRead:
            self.gps_data = self.uart_read(toRead).decode()


class GPS(UART):
    def __init__(self, gps_cfg):
        global gps_data_retrieve_queue
        super(UART, self).__init__(gps_cfg['UARTn'], gps_cfg['buadrate'], gps_cfg['databits'], gps_cfg['parity'], gps_cfg['stopbits'], gps_cfg['flowctl'])
        self.set_callback(gps_data_retrieve_cb)
        self.gps_data = ''
        gps_data_retrieve_queue = Queue(maxsize=8)
        _thread.start_new_thread(gps_data_retrieve_thread, (self,))

    def uart_read(self, nread):
        return super(GPS, self).read(nread).decode()

    def read(self):
        return self.gps_data

    def read_location_GxRMC(self):
        gps_data = self.read()
        rmc_re = ure.search(
            r"\$G[NP]RMC,[0-9]+\.[0-9]+,A,[0-9]+\.[0-9]+,[NS],[0-9]+\.[0-9]+,[EW],[0-9]+\.[0-9]+,[0-9]+\.[0-9]+,[0-9]+,,,[ADE],[SCUV]\*[0-9]+",
            gps_data)
        if rmc_re:
            return rmc_re.group(0)
        else:
            return ""

    def read_location_GxGGA(self):
        gps_data = self.read()
        gga_re = ure.search(
            r"\$G[BLPN]GGA,[0-9]+\.[0-9]+,[0-9]+\.[0-9]+,[NS],[0-9]+\.[0-9]+,[EW],[126],[0-9]+,[0-9]+\.[0-9]+,-*[0-9]+\.[0-9]+,M,-*[0-9]+\.[0-9]+,M,,\*[0-9]+",
            gps_data)
        if gga_re:
            return gga_re.group(0)
        else:
            return ""


class CellLocator(object):
    def __init__(self, cellLocator_cfg):
        self.cellLocator_cfg = cellLocator_cfg

    def read(self):
        return cellLocator.getLocation(
            self.cellLocator_cfg['serverAddr'],
            self.cellLocator_cfg['port'],
            self.cellLocator_cfg['token'],
            self.cellLocator_cfg['timeout'],
            self.cellLocator_cfg['profileIdx']
        )


class WiFiLocator(wifilocator):
    def __init__(self, wifiLocator_cfg):
        super(wifilocator, self).__init__(wifiLocator_cfg['token'])

    def read(self):
        return super(wifilocator, self).getwifilocator()


def loc_worker(argv):
    self = argv
    while True:
        trigger = self.trigger_queue.get()
        if trigger:
            data = self.read()
            if data and self.read_cb:
                self.read_cb(data)


class Location(GPS, CellLocator, WiFiLocator):
    gps_enabled = False
    cellLoc_enabled = False
    wifiLoc_enabled = False

    def __init__(self, read_cb, **kw):
        current_settings = settings.current_settings

        self.read_cb = read_cb

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps:
            if 'gps_cfg' in kw:
                super(GPS, self).__init__(kw['gps_cfg'])
                self.gps_enabled = True
            else:
                raise ValueError('Invalid gps init parameters.')

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.cell:
            if 'cellLocator_cfg' in kw:
                super(CellLocator, self).__init__(kw['cellLocator_cfg'])
                self.cellLoc_enabled = True
            else:
                raise ValueError('Invalid cell-locator init parameters.')

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.wifi:
            if 'wifiLocator_cfg' in kw:
                super(WiFiLocator, self).__init__(kw['wifiLocator_cfg'])
                self.wifiLoc_enabled = True
            else:
                raise ValueError('Invalid wifi-locator init parameters.')

        self.trigger_queue = Queue(maxsize=64)
        _thread.start_new_thread(loc_worker, (self,))

    def read(self):
        if self.gps_enabled:
            data = []
            r = super(GPS, self).read_location_GxRMC()
            if r:
                data.append(r)

            r = super(GPS, self).read_location_GxGGA()
            if r:
                data.append(r)

            if len(data):
                return (settings.default_values_app._loc_method.gps, data)

        if self.cellLoc_enabled:
            data = super(CellLocator, self).read()
            if data:
                return (settings.default_values_app._loc_method.cell, data)

        if self.wifiLoc_enabled:
            data = super(WiFiLocator, self).read()
            if data:
                return (settings.default_values_app._loc_method.wifi, data)

        return ()

    def trigger(self):
        self.trigger_queue.put(True)
