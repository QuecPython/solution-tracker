import utime
import quecgnss
from usr.libs import CurrentApp
from usr.libs.threading import Thread
from usr.libs.logging import getLogger
import _thread
from .import qth_client
try:
    from math import sin, asin, cos, radians, fabs, sqrt
except:
    from cmath import sin as csin, cos as ccos, pi

    def radians(x):
        return x * pi / 180.0
    
    def fabs(x):
        return x if x > 0 else -x

    def sin(x):
        return csin(x).real
    
    def cos(x):
        return ccos(x).real
    
    def asin(x):
        low, high = -1, 1
        while abs(high - low) > 1e-10:  # 精度控制
            mid = (low + high) / 2.0
            if sin(mid) < x:
                low = mid
            else:
                high = mid
        return (low + high) / 2.0


logger = getLogger(__name__)


EARTH_RADIUS = 6371  # 地球平均半径大约6371km
GLOBAL_DISTANCE = 0  # 里程km


def hav(theta):
    s = sin(theta / 2)
    return s * s


def gps_distance(lat0, lng0, lat1, lng1):
    # 用haversine公式计算球面两点间的距离
    # 经纬度转换成弧度
    lat0 = radians(lat0)
    lat1 = radians(lat1)
    lng0 = radians(lng0)
    lng1 = radians(lng1)
    dlng = fabs(lng0 - lng1)
    dlat = fabs(lat0 - lat1)
    h = hav(dlat) + cos(lat0) * cos(lat1) * hav(dlng)
    distance = 2 * EARTH_RADIUS * asin(pow(h, 0.5))  # km
    # distance = int(distance * 1000)  # m
    return distance


class NmeaDict(dict):

    @classmethod
    def load(cls, raw):
        items = {}
        for line in raw.split('\r\n'):
            try:
                tail_index = line.rfind('*')
                if tail_index == -1:
                    continue
                head_index = line.rfind('$', 0, tail_index)
                if head_index == -1:
                    continue
                crc = int(line[tail_index + 1:tail_index + 3], 16)
                if cls.checksum(line[head_index + 1:tail_index]) != crc:
                    raise ValueError('CRC check failed')
                cmdlist = line[head_index:tail_index].split(',')
                # print(line[head_index:])
                if cmdlist[0] not in items:
                    items[cmdlist[0]] = []
                items[cmdlist[0]].append(line)
            except Exception as e:
                # logger.debug('parse nmea line error: {}; pass it: {}'.format(e, line))
                continue
        return cls(items)

    @staticmethod
    def checksum(data):
        crc = ord(data[0])
        for one in (ord(_) for _ in data[1:]):
            crc ^= one
        return crc


class GnssService(object):

    def __init__(self, app=None):
        self.__gnss = quecgnss
        if app is not None:
            self.init_app(app)

    def __str__(self):
        return '{}'.format(type(self).__name__)

    def init_app(self, app):
        app.register('gnss_service', self)

    def load(self):
        logger.info('loading {} extension, init quecgnss will take some seconds'.format(self))
        result = self.init()
        logger.info('{} init gnss res: {}'.format(self, result))
        if result:
            Thread(target=self.start_update).start()

    def init(self):
        if self.__gnss.init() != 0:
            logger.warn('{} gnss init FAILED'.format(self))
            return False
        return True

    def status(self):
        # 0	int	GNSS模块处于关闭状态
        # 1	int	GNSS模块固件升级中
        # 2	int GNSS模块定位中，这种模式下即可开始读取GNSS定位数据，定位数据是否有效需要用户获取到定位数据后，解析对应语句来判断，比如判断GNRMC语句的status是 A 还是 V，A 表示定位有效，V表示定位无效。
        return self.__gnss.get_state()

    def enable(self, flag=True):
        return self.__gnss.gnssEnable(bool(flag)) == 0

    def read(self, size=4096):
        raw = self.__gnss.read(size)
        if raw != -1:
            size, data = raw
            # logger.debug('gnss read raw {} bytes data:\n{}'.format(size, data))
            return NmeaDict.load(data)

    def start_update(self):
        prev_lat_and_lng = None

        while True:
            nmea_dict = self.read()
            if nmea_dict is None:
                utime.sleep(3)
                continue

            nmea_data = None

            if nmea_data is None:
                if "$GNRMC" in nmea_dict:
                    for temp in nmea_dict["$GNRMC"]:
                        nmea_tuple = temp.split(",")
                        if nmea_tuple[2] == "A":
                            nmea_data = temp

                            lat_string = nmea_tuple[3]
                            lat_high = float(lat_string[:2])
                            lat_low = float(lat_string[2:]) / 60
                            lat = lat_high + lat_low
                            if nmea_tuple[4] == "S":
                                lat = -lat
                            
                            lng_string = nmea_tuple[5]  # 11755.787896484374（单位：分）
                            lng_high = float(lng_string[:3])
                            lng_low = float(lng_string[3:]) / 60
                            lng = lng_high + lng_low
                            if nmea_tuple[6] == "W":
                                lng = -lng

                            break

            if nmea_data is None:
                if "$GNGGA" in nmea_dict:
                    for temp in nmea_dict["$GNGGA"]:
                        nmea_tuple = temp.split(",")
                        if nmea_tuple[6] != "0":
                            nmea_data = temp

                            lat_string = nmea_tuple[2]
                            lat_high = float(lat_string[:2])
                            lat_low = float(lat_string[2:]) / 60
                            lat = lat_high + lat_low
                            if nmea_tuple[3] == "S":
                                lat = -lat

                            lng_string = nmea_tuple[4]  # 11755.787896484374（单位：分）
                            lng_high = float(lng_string[:3])
                            lng_low = float(lng_string[3:]) / 60
                            lng = lng_high + lng_low
                            if nmea_tuple[5] == "W":
                                lng = -lng
                                
                            break
            
            if nmea_data is not None:
                # logger.debug("GPS data: {}".format(nmea_data))
                # logger.debug("prev_lat_and_lng: {}".format(prev_lat_and_lng))
                logger.debug("lat_and_lng: {}".format((lat, lng)))
                if prev_lat_and_lng is None:
                    # 首次定位
                    for _ in range(3):
                        with CurrentApp().qth_client:
                            if CurrentApp().qth_client.sendGnss(nmea_data):
                                prev_lat_and_lng = (lat, lng)
                                logger.error("send gnss to qth server success")
                                break
                    else:
                        logger.error("send gnss to qth server fail")
                else:
                    # 或者位移超过 50m，则上报
                    distance = gps_distance(prev_lat_and_lng[0], prev_lat_and_lng[1], lat, lng)
                    logger.debug('distance delta: {:f}'.format(distance))
                    if distance >= 0.05:
                        for _ in range(3):
                            with CurrentApp().qth_client:
                                if CurrentApp().qth_client.sendGnss(nmea_data):
                                    prev_lat_and_lng = (lat, lng)
                                    logger.error("send gnss to qth server success")
                                    break
                        else:
                            logger.error("send gnss to qth server fail")
            utime.sleep(3)


