# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ure
import utime
import osTimer
import _thread
import cellLocator

from queue import Queue
from machine import UART
from wifilocator import wifilocator

import usr.settings as settings
from usr.logging import getLogger
from usr.common import Singleton

try:
    import quecgnss
except ImportError:
    quecgnss = None

log = getLogger(__name__)

gps_data_retrieve_queue = None

_gps_read_lock = _thread.allocate_lock()


def gps_read_lock(func):
    def wrapperd_fun(*args, **kwargs):
        with _gps_read_lock:
            return func(*args, **kwargs)
    return wrapperd_fun


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
        if gps_data_retrieve_queue.size() >= 8:
            gps_data_retrieve_queue.get()
        gps_data_retrieve_queue.put(toRead)


class GPS(Singleton):
    def __init__(self, gps_cfg):
        self.gps_data = ''
        self.gps_cfg = gps_cfg
        self.__gps_timer = osTimer()
        self.__first_break = 0
        self.__second_break = 0
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
        gps_data_retrieve_queue = Queue(maxsize=8)
        self.uart_open()

    def uart_open(self):
        self.uart_obj = UART(
            self.gps_cfg['UARTn'], self.gps_cfg['buadrate'], self.gps_cfg['databits'],
            self.gps_cfg['parity'], self.gps_cfg['stopbits'], self.gps_cfg['flowctl']
        )
        self.uart_obj.set_callback(gps_data_retrieve_cb)

    def uart_close(self):
        self.uart_obj.close()

    def first_gps_timer_callback(self, args):
        global gps_data_retrieve_queue
        self.__first_break = 1
        if gps_data_retrieve_queue is not None:
            gps_data_retrieve_queue.put(0)
            log.debug('gps_data_retrieve_queue.put(0)')

    def second_gps_timer_callback(self, args):
        global gps_data_retrieve_queue
        self.__second_break = 1
        if gps_data_retrieve_queue is not None:
            gps_data_retrieve_queue.put(0)

    def uart_read(self):
        self.uart_open()
        log.debug('uart_read start')
        global gps_data_retrieve_queue

        while self.__first_break == 0:
            self.__gps_timer.start(50, 0, self.first_gps_timer_callback)
            nread = gps_data_retrieve_queue.get()
            log.debug('__first_break nread: %s' % nread)
            data = self.uart_obj.read(nread).decode()
            log.debug('__first_break data: %s' % data)
            self.__gps_timer.stop()
        self.__first_break = 0

        data = ''
        rmc_data = ''
        gga_data = ''
        vtg_data = ''
        while self.__second_break == 0:
            self.__gps_timer.start(1500, 0, self.second_gps_timer_callback)
            nread = gps_data_retrieve_queue.get()
            log.debug('__second_break nread: %s' % nread)
            if nread:
                data += self.uart_obj.read(nread).decode()
                if not rmc_data:
                    rmc_data = self.read_location_GxRMC(data)
                if not gga_data:
                    gga_data = self.read_location_GxGGA(data)
                if not vtg_data:
                    vtg_data = self.read_location_GxVTG(data)
                if rmc_data and gga_data and vtg_data:
                    self.__second_break = 1
            self.__gps_timer.stop()
        log.debug('__second_break(uart_read) data: %s' % data)
        self.__second_break = 0

        self.uart_close()
        return data

    def quecgnss_read(self):
        if quecgnss.get_state() == 0:
            quecgnss.gnssEnable(1)

        while self.__first_break == 0:
            self.__gps_timer.start(50, 0, self.first_gps_timer_callback)
            data = quecgnss.read(1024)
            self.__gps_timer.stop()
        self.__first_break = 0

        data = ''
        rmc_data = ''
        gga_data = ''
        vtg_data = ''
        count = 0
        while self.__second_break == 0:
            self.__gps_timer.start(1500, 0, self.second_gps_timer_callback)
            gnss_data = quecgnss.read(1024)
            if gnss_data and gnss_data[1]:
                data += gnss_data[1].decode() if len(gnss_data) > 1 and gnss_data[1] else ''
                if not rmc_data:
                    rmc_data = self.read_location_GxRMC(data)
                if not gga_data:
                    gga_data = self.read_location_GxGGA(data)
                if not vtg_data:
                    vtg_data = self.read_location_GxVTG(data)
                if rmc_data and gga_data and vtg_data:
                    self.__second_break = 1
            self.__gps_timer.stop()

            if count > 5:
                self.__second_break = 1
            count += 1
            utime.sleep_ms(300)
        self.__second_break = 0

        return data

    @gps_read_lock
    def read(self):
        current_settings = settings.settings.get()
        if current_settings['sys']['gps_mode'] & settings.default_values_sys._gps_mode.external:
            self.gps_data = self.uart_read().decode()
        elif current_settings['sys']['gps_mode'] & settings.default_values_sys._gps_mode.internal:
            self.gps_data = self.quecgnss_read()
        else:
            self.gps_data = ''
        return self.gps_data

    def read_location_GxRMC(self, gps_data):
        rmc_re = ure.search(
            r"\$G[NP]RMC,\d*\.*\d*,[AV]*,\d*\.*\d*,[NS]*,\d*\.*\d*,[EW]*,\d*\.*\d*,\d*\.*\d*,\d*,\d*\.*\d*,[EW]*,[ADEN]*,[SCUV]*\**\d*",
            gps_data)
        if rmc_re:
            return rmc_re.group(0)
        return ""

    def read_location_GxGGA(self, gps_data):
        gga_re = ure.search(
            r"\$G[BLPN]GGA,\d*\.*\d*,\d*\.*\d*,[NS]*,\d*\.*\d*,[EW]*,[0126]*,\d*,\d*\.*\d*,-*\d*\.*\d*,M,-*\d*\.*\d*,M,\d*,\**\d*",
            gps_data)
        if gga_re:
            return gga_re.group(0)
        return ""

    def read_location_GxVTG(self, gps_data):
        vtg_re = ure.search(r"\$G[NP]VTG,\d*\.*\d*,T,\d*\.*\d*,M,\d*\.*\d*,N,\d*\.*\d*,K,[ADEN]*\**\d*", gps_data)
        if vtg_re:
            return vtg_re.group(0)
        return ""

    def read_location_GxVTG_speed(self, gps_data):
        vtg_data = self.read_location_GxVTG(gps_data)
        if vtg_data:
            speed_re = ure.search(r",N,\d+\.\d+,K,", vtg_data)
            if speed_re:
                return speed_re.group(0)[3:-3]
        return ""

    def read_quecIot(self):
        res = {}
        data = []
        gps_data = self.read()
        r = self.read_location_GxRMC(gps_data)
        if r:
            data.append(r)

        r = self.read_location_GxGGA(gps_data)
        if r:
            data.append(r)

        r = self.read_location_GxVTG(gps_data)
        if r:
            data.append(r)
        if data:
            res = {'gps': data}

        return res

    def read_aliyun(self):
        gps_info = {}
        gps_data = self.read()
        gga_data = self.read_location_GxGGA(gps_data)
        data = {}
        if gga_data:
            Latitude_re = ure.search(r",[0-9]+\.[0-9]+,[NS],", gga_data)
            if Latitude_re:
                data['Latitude'] = round(float(Latitude_re.group(0)[1:-3]), 2)
            Longtitude_re = ure.search(r",[0-9]+\.[0-9]+,[EW],", gga_data)
            if Longtitude_re:
                data['Longtitude'] = round(float(Longtitude_re.group(0)[1:-3]), 2)
            Altitude_re = ure.search(r"-*[0-9]+\.[0-9]+,M,", gga_data)
            if Altitude_re:
                data['Altitude'] = round(float(Altitude_re.group(0)[:-3]), 2)
            if data:
                data['CoordinateSystem'] = 1
        if data:
            gps_info = {'GeoLocation': data}
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
        return {'non_gps': ['LBS']}

    def read_aliyun(self):
        gps_info = {}
        gps_data = self.read()
        if gps_data:
            gps_info = {'GeoLocation': {'Longtitude': round(gps_data[0], 2), 'Latitude': round(gps_data[1], 2), 'Altitude': 0.0, 'CoordinateSystem': 1}}
        return gps_info


class WiFiLocator(object):
    def __init__(self, wifiLocator_cfg):
        self.wifilocator_obj = wifilocator(wifiLocator_cfg['token'])

    def read(self):
        return self.wifilocator_obj.getwifilocator()

    def read_quecIot(self):
        # TODO: {'non_gps': []}
        return {}

    def read_aliyun(self):
        gps_info = {}
        gps_data = self.read()
        if gps_data:
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

            if data:
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
