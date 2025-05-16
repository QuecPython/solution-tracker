from machine import I2C
from usr.libs.collections import Integer


class I2CIOWrapper(object):

    class I2CReadError(Exception):
        pass

    class I2CWriteError(Exception):
        pass

    def __init__(self, i2c, slaveaddr):
        if not isinstance(i2c, I2C):
            raise TypeError('`i2c` should be machine.I2C type')
        self.__i2c = i2c
        self.__slaveaddr = slaveaddr


    def read(self, addr, size=1, delay=0):
        if size <= 0:
            raise ValueError('`size` should be greater than 0')
        data = bytearray(size)
        if self.__i2c.read(self.__slaveaddr, addr, len(addr), data, size, delay) != 0:
            raise self.I2CReadError("slave 0x{:X} read failed".format(self.__slaveaddr))
        return data

    def write(self, addr, data):
        if not isinstance(data, (bytearray, bytes)):
            raise TypeError('`data` should be bytearray or bytes')
        if self.__i2c.write(self.__slaveaddr, addr, len(addr), data, len(data)) != 0:
            raise self.I2CWriteError("slave 0x{:X} write failed".format(self.__slaveaddr))

    def readByte(self, addr, byteorder="big", signed=False):
        return Integer.fromBytes(self.read(b'' if addr is None else bytes([addr]), 1), byteorder=byteorder, signed=signed)

    def writeByte(self, addr, value):
        return self.write(b'' if addr is None else bytes([addr]), bytes([value]))

    def readWord(self, addr, byteorder="big", signed=False):
        return Integer.fromBytes(self.read(b'' if addr is None else bytes([addr]), 2), byteorder=byteorder, signed=signed)

    def writeWord(self, addr, value, byteorder="big"):
        return self.write(b'' if addr is None else bytes([addr]), Integer(value).toBytes(2, byteorder=byteorder))
