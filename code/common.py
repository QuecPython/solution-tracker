import _thread
from misc import Power


class Singleton(object):
    _instance_lock = _thread.allocate_lock()

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance_dict'):
            Singleton.instance_dict = {}

        if str(cls) not in Singleton.instance_dict.keys():
            with Singleton._instance_lock:
                _instance = super().__new__(cls)
                Singleton.instance_dict[str(cls)] = _instance

        return Singleton.instance_dict[str(cls)]


def numiter():
    for i in range(99999):
        yield i


def power_restart():
    Power.powerRestart()
