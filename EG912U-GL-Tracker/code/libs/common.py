import ql_fs
from .threading import Lock


def deepcopy(obj):
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return type(obj)((deepcopy(item) for item in obj))
    elif isinstance(obj, dict):
        return {k: deepcopy(v) for k, v in obj.items()}
    else:
        raise TypeError('unsupported for \"{}\" type'.format(type(obj)))


class Storage(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lock__ = Lock()
        self.__storage_path__ = None

    def __enter__(self):
        self.__lock__.acquire()
        return self

    def __exit__(self, *args, **kwargs):
        self.__lock__.release()

    def __from_json(self, path):
        if self.__storage_path__ is not None:
            raise ValueError('storage already init from \"{}\"'.format(self.__storage_path__))
        if not ql_fs.path_exists(path):
            ql_fs.touch(path, {})
        else:
            self.update(ql_fs.read_json(path))

    def init(self, path):
        if path.endswith('.json'):
            self.__from_json(path)
        else:
            raise ValueError('\"{}\" file type not supported'.format(path))
        self.__storage_path__ = path

    def save(self):
        if self.__storage_path__ is None:
            raise ValueError('storage path not existed, did you init?')
        ql_fs.touch(self.__storage_path__, self)
