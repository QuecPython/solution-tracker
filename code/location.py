
import ure
import _thread
import cellLocator
import usr.settings as settings

from queue import Queue
from machine import UART
from usr.logging import getLogger
from usr.common import Singleton
from wifilocator import wifilocator

try:
    import quecgnss
except ImportError:
    quecgnss = None

log = getLogger(__name__)

gps_data_retrieve_queue = None


class LocationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


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
        self.gps_data = ''
        self.gps_cfg = gps_cfg
        current_settings = settings.settings.get()
        if current_settings['sys']['gps_mode'] & settings.default_values_sys._gps_mode.external:
            self.uart_init()
        elif current_settings['sys']['gps_mode'] & settings.default_values_sys._gps_mode.internal:
            if quecgnss:
                quecgnss.init()
            else:
                raise LocationError('quecgnss import error.')
            self.quecgnss_read()

    def uart_init(self):
        global gps_data_retrieve_queue
        self.uart_obj = UART(
            self.gps_cfg['UARTn'], self.gps_cfg['buadrate'], self.gps_cfg['databits'],
            self.gps_cfg['parity'], self.gps_cfg['stopbits'], self.gps_cfg['flowctl']
        )
        self.uart_obj.set_callback(gps_data_retrieve_cb)
        gps_data_retrieve_queue = Queue(maxsize=8)
        _thread.start_new_thread(gps_data_retrieve_thread, (self,))

    def uart_read(self, nread):
        return self.uart_obj.read(nread).decode()

    def quecgnss_read(self):
        if quecgnss.get_state() == 0:
            quecgnss.gnssEnable(1)

        data = quecgnss.read(4096)
        self.gps_data = data[1].decode()

        return self.gps_data

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

    def read_quecIot(self):
        data = []
        r = self.read_location_GxRMC()
        if r:
            data.append(r)

        r = self.read_location_GxGGA()
        if r:
            data.append(r)

        r = self.read_location_GxVTG()
        if r:
            data.append(r)

        return data

    def read_aliyun(self):
        gga_data = self.read_location_GxGGA()
        gps_data = {'CoordinateSystem': 1}
        if gga_data:
            Latitude_re = ure.search(r",[0-9]+\.[0-9]+,[NS],", gga_data)
            if Latitude_re:
                gps_data['Latitude'] = round(float(Latitude_re.group(0)[1:-3]), 2)
            Longtitude_re = ure.search(r",[0-9]+\.[0-9]+,[EW],", gga_data)
            if Longtitude_re:
                gps_data['Longtitude'] = round(float(Longtitude_re.group(0)[1:-3]), 2)
            Altitude_re = ure.search(r"-*[0-9]+\.[0-9]+,M,", gga_data)
            if Altitude_re:
                gps_data['Altitude'] = round(float(Altitude_re.group(0)[:-3]), 2)
        gps_info = {'GeoLocation': gps_data}
        return gps_info


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

    def read_quecIot(self):
        return ['LBS']

    def read_aliyun(self):
        gps_data = self.read()
        gps_info = {'GeoLocation': {'Longtitude': round(gps_data[0], 2), 'Latitude': round(gps_data[1], 2), 'Altitude': 0.0, 'CoordinateSystem': 1}}
        return gps_info


class WiFiLocator(object):
    def __init__(self, wifiLocator_cfg):
        self.wifilocator_obj = wifilocator(wifiLocator_cfg['token'])

    def read(self):
        return self.wifilocator_obj.getwifilocator()

    def read_quecIot(self):
        return []

    def read_aliyun(self):
        gps_data = self.read()
        gps_info = {'GeoLocation': {'Longtitude': round(gps_data[0], 2), 'Latitude': round(gps_data[1], 2), 'Altitude': 0.0, 'CoordinateSystem': 1}}
        return gps_info


class Location(Singleton):
    gps = None
    cellLoc = None
    wifiLoc = None

    def __init__(self):
        self._locater_init()

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
        current_settings = settings.settings.get()

        if self.gps:
            if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
                data = self.gps.read_quecIot()
            elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
                data = self.gps.read_aliyun()
            else:
                data = self.gps.read()

            if len(data):
                return (settings.default_values_app._loc_method.gps, data)

        if self.cellLoc:
            if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
                data = self.cellLoc.read_quecIot()
            elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
                data = self.cellLoc.read_aliyun()
            else:
                data = self.cellLoc.read()

            if data:
                return (settings.default_values_app._loc_method.cell, data)

        if self.wifiLoc:
            if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
                data = self.wifiLoc.read_quecIot()
            elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
                data = self.wifiLoc.read_aliyun()
            else:
                data = self.wifiLoc.read()

            if data:
                return (settings.default_values_app._loc_method.wifi, data)

        return ()
