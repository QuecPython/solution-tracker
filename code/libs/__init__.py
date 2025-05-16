import sys
import net
import sim
import modem
from misc import Power
from .common import Storage
from .collections import OrderedDict, Singleton


@Singleton
class _AppCtxGlobals(object):

    def setDefault(self, name, value):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            setattr(self, name, value)
            return value

    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default

    def set(self, name, value):
        setattr(self, name, value)


G = _AppCtxGlobals


@Singleton
class Application(object):
    """Application Class"""

    def __init__(self, name, version='1.0.0'):
        self.__name = name
        self.config = Storage()
        self.__version = version
        self.__extensions = OrderedDict()

    def __repr__(self):
        return '{}(name=\"{}\", version=\"{}\")'.format(type(self).__name__, self.name, self.version)

    def __getattr__(self, name):
        return self.__extensions[name]

    def register(self, name, ext):
        if name in self.__extensions:
            raise ValueError('extension name \"{}\" already in use'.format(name))
        self.__extensions[name] = ext

    def __powerOnPrintOnce(self):
        output = '==================================================\r\n'
        output += 'APP_NAME         : {}\r\n'
        output += 'APP_VERSION      : {}\r\n'
        output += 'FIRMWARE_VERSION : {}\r\n'
        output += 'POWERON_REASON   : {}\r\n'
        output += 'DEVICE_IMEI      : {}\r\n'
        output += 'SIM_STATUS       : {}\r\n'
        output += 'NET_STATUS       : {}\r\n'
        output += '=================================================='
        print(output.format(
            self.name,
            self.version,
            modem.getDevFwVersion(),
            Power.powerOnReason(),
            modem.getDevImei(),
            sim.getStatus(),
            net.getState()[1][0]
        ))

    def __loadExtensions(self):
        for ext in self.__extensions.values():
            if not hasattr(ext, 'load'):
                continue
            try:
                ext.load()
            except Exception as e:
                sys.print_exception(e)

    def run(self):
        self.__powerOnPrintOnce()
        self.__loadExtensions()

    @property
    def version(self):
        return self.__version

    @property
    def name(self):
        return self.__name


CurrentApp = Application
