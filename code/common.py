import _thread

from misc import Power
from usr.battery import Battery


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


class ControllerError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Controller(Singleton):
    def __init__(self, remote):
        self.remote = remote

    def power_switch(self, perm, flag=None, *args):
        if perm == 'r':
            self.remote.post_data(self.remote.DATA_NON_LOCA, {'power_switch': True})
        elif perm == 'w':
            if flag is True:
                # TODO: Get other model info
                model_info = {}
                model_info['power_switch'] = flag
                self.remote.post_data(self.remote.DATA_NON_LOCA, model_info)
            elif flag is False:
                # TODO: Get other model info
                model_info = {}
                model_info['power_switch'] = flag
                self.remote.post_data(self.remote.DATA_NON_LOCA, model_info)
                Power.powerDown()
            else:
                pass
        else:
            raise ControllerError('Controller switch permission error %s.' % perm)

    def energy(self, perm, *args):
        if perm == 'r':
            battery_energy = Battery().energy()
            self.remote.post_data(self.remote.DATA_NON_LOCA, {'energy': battery_energy})
        else:
            raise ControllerError('Controller energy permission error %s.' % perm)
