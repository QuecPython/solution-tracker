
import ure
import utime
import _thread
import cellLocator
import usr.settings as settings

from queue import Queue
from machine import UART
from usr.logging import getLogger
from usr.common import Singleton
from wifilocator import wifilocator

log = getLogger(__name__)

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


class GPS(Singleton):
    def __init__(self, gps_cfg):
        global gps_data_retrieve_queue
        self.uart_obj = UART(
            gps_cfg['UARTn'], gps_cfg['buadrate'], gps_cfg['databits'],
            gps_cfg['parity'], gps_cfg['stopbits'], gps_cfg['flowctl']
        )
        self.uart_obj.set_callback(gps_data_retrieve_cb)
        self.gps_data = ''
        gps_data_retrieve_queue = Queue(maxsize=8)
        _thread.start_new_thread(gps_data_retrieve_thread, (self,))

    def uart_read(self, nread):
        return self.uart_obj.read(nread).decode()

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

    def read_location_GxVTG(self):
        gps_data = self.read()
        vtg_re = ure.search(r"\$G[NP]VTG,[0-9]+\.[0-9]+,T,([0-9]+\.[0-9]+)??,M,[0-9]+\.[0-9]+,N,[0-9]+\.[0-9]+,K,[ADEN]\*\w*", gps_data)
        if vtg_re:
            return vtg_re.group(0)
        else:
            return ""

    def read_location_GxVTG_speed(self):
        vtg_data = self.read_location_GxVTG()
        if vtg_data:
            speed_re = ure.search(r",N,[0-9]+\.[0-9]+,K,", vtg_data)
            if speed_re:
                return speed_re.group(0)[3:-3]

        return ""


class CellLocator(object):
    def __init__(self, cellLocator_cfg):
        self.cellLocator_cfg = cellLocator_cfg

    def read(self):
        return ['LBS']

    def get_location(self):
        return cellLocator.getLocation(
            self.cellLocator_cfg['serverAddr'],
            self.cellLocator_cfg['port'],
            self.cellLocator_cfg['token'],
            self.cellLocator_cfg['timeout'],
            self.cellLocator_cfg['profileIdx']
        )


class WiFiLocator(object):
    def __init__(self, wifiLocator_cfg):
        self.wifilocator_obj = wifilocator(wifiLocator_cfg['token'])

    def read(self):
        return []

    def get_location(self):
        return self.wifilocator_obj.getwifilocator()


def loc_worker(argv):
    self = argv
    while True:
        trigger = self.trigger_queue.get()
        if trigger:
            data = None
            retry = 0
            while retry < 3:
                data = self.read()
                if data:
                    break
                else:
                    retry += 1
                    utime.sleep(1)
            log.debug('location data info:', data)
            if data and self.read_cb:
                self.read_cb(data)


class Location(Singleton):
    gps = None
    cellLoc = None
    wifiLoc = None

    def __init__(self, read_cb):
        self.read_cb = read_cb
        self.trigger_queue = Queue(maxsize=64)
        _thread.start_new_thread(loc_worker, (self,))

    def _locater_init(self):
        current_settings = settings.settings.get()
        locator_init_params = current_settings['sys']['locator_init_params']

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps:
            if self.gps is None:
                if 'gps_cfg' in locator_init_params:
                    self.gps = GPS(locator_init_params['gps_cfg'])
                else:
                    raise ValueError('Invalid gps init parameters.')
        else:
            self.gps = None

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.cell:
            if self.cellLoc is None:
                if 'cellLocator_cfg' in locator_init_params:
                    self.cellLoc = CellLocator(locator_init_params['cellLocator_cfg'])
                else:
                    raise ValueError('Invalid cell-locator init parameters.')
        else:
            self.cellLoc = None

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.wifi:
            if self.wifiLoc is None:
                if 'wifiLocator_cfg' in locator_init_params:
                    self.wifiLoc = WiFiLocator(locator_init_params['wifiLocator_cfg'])
                else:
                    raise ValueError('Invalid wifi-locator init parameters.')
        else:
            self.wifiLoc = None

    def read(self):
        self._locater_init()

        if self.gps:
            data = []
            r = self.gps.read_location_GxRMC()
            if r:
                data.append(r)

            r = self.gps.read_location_GxGGA()
            if r:
                data.append(r)

            if len(data):
                return (settings.default_values_app._loc_method.gps, data)

        if self.cellLoc:
            data = self.cellLoc.read()
            if data:
                return (settings.default_values_app._loc_method.cell, data)

        if self.wifiLoc:
            data = self.wifiLoc.read()
            if data:
                return (settings.default_values_app._loc_method.wifi, data)

        return ()

    def trigger(self):
        self.trigger_queue.put(True)
