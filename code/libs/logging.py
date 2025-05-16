import utime
import sys
import uio as io
import _thread


class Level(object):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    CRITICAL = 4


_levelToName = {
    Level.CRITICAL: 'CRITICAL',
    Level.ERROR: 'ERROR',
    Level.WARN: 'WARN',
    Level.INFO: 'INFO',
    Level.DEBUG: 'DEBUG'
}

_nameToLevel = {
    'CRITICAL': Level.CRITICAL,
    'ERROR': Level.ERROR,
    'WARN': Level.WARN,
    'INFO': Level.INFO,
    'DEBUG': Level.DEBUG,
}


def getLevelName(level):
    if level not in _levelToName:
        raise ValueError('unknown level \"{}\", choose from <class Level>.'.format(level))
    return _levelToName[level]


def getNameLevel(name):
    temp = name.upper()
    if temp not in _nameToLevel:
        raise ValueError('\"{}\" is not valid. choose from [{}]'.format(name, list(_nameToLevel.keys())))
    return _nameToLevel[temp]


class BasicConfig(object):
    logger_register_table = {}
    basic_configure = {
        'level': Level.WARN,
        'debug': True,
        'stream': sys.stdout
    }

    @classmethod
    def getLogger(cls, name):
        if name not in cls.logger_register_table:
            logger = Logger(name)
            cls.logger_register_table[name] = logger
        else:
            logger = cls.logger_register_table[name]
        return logger

    @classmethod
    def update(cls, **kwargs):
        level = kwargs.pop('level', None)
        if level is not None:
            kwargs['level'] = getNameLevel(level)
        return cls.basic_configure.update(kwargs)

    @classmethod
    def get(cls, key):
        return cls.basic_configure[key]

    @classmethod
    def set(cls, key, value):
        if key == 'level':
            value = getNameLevel(value)
        cls.basic_configure[key] = value


class Logger(object):
    lock = _thread.allocate_lock()

    def __init__(self, name):
        self.name = name

    @staticmethod
    def __get_formatted_time():
        # (2023, 9, 30, 11, 11, 41, 5, 273)
        cur_time_tuple = utime.localtime()
        return '{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(
            cur_time_tuple[0],
            cur_time_tuple[1],
            cur_time_tuple[2],
            cur_time_tuple[3],
            cur_time_tuple[4],
            cur_time_tuple[5]
        )

    def log(self, level, *message):
        if not BasicConfig.get('debug'):
            if level < BasicConfig.get('level'):
                return
        stream = BasicConfig.get('stream')
        prefix = '[{}][{}][{}]'.format(
            self.__get_formatted_time(),
            getLevelName(level),
            self.name,
        )
        with self.lock:
            print(prefix, *message, file=stream)
            if isinstance(stream, io.TextIOWrapper):
                stream.flush()

    def debug(self, *message):
        self.log(Level.DEBUG, *message)

    def info(self, *message):
        self.log(Level.INFO, *message)

    def warn(self, *message):
        self.log(Level.WARN, *message)

    def error(self, *message):
        self.log(Level.ERROR, *message)

    def critical(self, *message):
        self.log(Level.CRITICAL, *message)


def getLogger(name):
    return BasicConfig.getLogger(name)
