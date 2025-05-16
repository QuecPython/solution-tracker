"""
SHTC3 temperature and humidity sensor driver.
The SHTC3 is a digital humidity and temperature sensor designed especially for battery-driven high-volume consumer electronics applications.
"""

import utime
from usr.libs.i2c import I2CIOWrapper


SHTC3_SLAVE_ADDR = 0x70

# Commands
SHTC3_WAKEUP            =   b"\x35\x17"
SHTC3_SLEEP		        =	b"\xB0\x98"
SHTC3_NM_CE_READ_TH     =	b"\x7C\xA2"
SHTC3_NM_CE_READ_RH     =	b"\x5C\x24"
SHTC3_NM_CD_READ_TH     =	b"\x78\x66"
SHTC3_NM_CD_READ_RH     =	b"\x58\xE0"
SHTC3_LM_CE_READ_TH     =	b"\x64\x58"
SHTC3_LM_CE_READ_RH     =	b"\x44\xDE"
SHTC3_LM_CD_READ_TH     =	b"\x60\x9C"
SHTC3_LM_CD_READ_RH     =	b"\x40\x1A"
SHTC3_SOFTWARE_RESET    =	b"\x40\x1A"
SHTC3_ID                = 	b"\xEF\xC8"


class Shtc3(I2CIOWrapper):

    def init(self):
        chip_id = self.getChipId()
        if chip_id != 0x0807:
            raise ValueError("{} get wrong chip id: {}".format(type(self).__name__, chip_id))
        self.soft_reset()

    def getChipId(self):
        id = int.from_bytes(self.read(SHTC3_ID, 2), "big")
        return id & 0x0807

    def wakeup(self):
        self.write(SHTC3_WAKEUP, b'')
        utime.sleep_ms(30)

    def sleep(self):
        self.write(SHTC3_SLEEP, b'')

    def soft_reset(self):
        self.write(SHTC3_SOFTWARE_RESET, b'')
        utime.sleep_ms(30)

    @staticmethod
    def checkCrc(data, checksum):
        crc = 0xFF
        for one in data:
            crc ^= one
            for _ in range(8):
                if(crc & 0x80):
                    crc = (crc << 1) ^ 0x131
                else:
                    crc = crc << 1
        return crc == checksum

    def __getValue(self):
        utime.sleep_ms(20)
        data = self.read(b'', 3)
        if self.checkCrc(data[:2], data[2]):
            return data[0] << 8 | data[1]

    def getTempValue(self):
        """Calculate the temperature value."""
        self.write(b'', SHTC3_NM_CD_READ_TH)
        value = self.__getValue()
        if value is not None:
            value = 175 * value / 65536.0 - 45.0
            return round(value, 2)
        return 0

    def getHumiValue(self):
        """Calculate the humidity value."""
        self.write(b'', SHTC3_NM_CD_READ_RH)
        value = self.__getValue()
        if value is not None:
            value = 100 * value / 65536.0
            return round(value, 2)
        return 0
    
    def getTempAndHumi(self):
        self.wakeup()
        temp = self.getTempValue()
        humi = self.getHumiValue()
        self.sleep()
        return temp, humi


if __name__ == "__main__":
    from machine import I2C
    shtc3_dev = Shtc3(I2C(I2C.I2C1, I2C.STANDARD_MODE), SHTC3_SLAVE_ADDR)
    shtc3_dev.init()
    for i in range(100):
        shtc3_dev.wakeup()
        temp = shtc3_dev.getTempValue()
        humi = shtc3_dev.getHumiValue()
        shtc3_dev.sleep()
        print("Temperature: {:.2f}°C , Humidity: {:.2f} %\n".format(temp, humi))
