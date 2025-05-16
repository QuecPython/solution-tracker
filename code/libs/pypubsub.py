"""基于 QuecPython 的订阅/发布机制"""


from usr.libs.threading import Thread, Queue, Lock


class Publisher(object):
    
    def __init__(self):
        self.__q = Queue()
        self.__topic_manager_lock = Lock()
        self.__topic_manager = {}
        self.__listen_thread = Thread(target=self.__listen_worker)
    
    def listen(self):
        self.__listen_thread.start()

    def __listen_worker(self):
        while True:
            topic, messages = self.__q.get()
            # print("topic: {}, messages: {}".format(topic, messages))
            with self.__topic_manager_lock:
                for listener in self.__topic_manager.setdefault(topic, []):
                    try:
                        listener(**messages)
                    except Exception as e:
                        print("listener error:", str(e))

    def publish(self, topic, **kwargs):
        self.__q.put((topic, kwargs))

    def subscribe(self, topic, listener):
        with self.__topic_manager_lock:
            listener_list = self.__topic_manager.setdefault(topic, [])
            listener_list.append(listener)

    def unsubscribe(self, topic, listener):
        with self.__topic_manager_lock:
            listener_list = self.__topic_manager.setdefault(topic, [])
            try:
                listener_list.remove(listener)
            except ValueError:
                pass


# global publisher
__publisher__ = None


def get_default_publisher():
    global __publisher__
    if __publisher__ is None:
        __publisher__ = Publisher()
        __publisher__.listen()
    return __publisher__



def publish(topic, **kwargs):
    """订阅消息"""
    pub = get_default_publisher()
    pub.publish(topic, **kwargs)


def subscribe(topic, listener):
    """订阅消息"""
    pub = get_default_publisher()
    pub.subscribe(topic, listener)


def unsubscribe(topic, listener):
    """取消订阅消息"""
    pub = get_default_publisher()
    pub.unsubscribe(topic, listener)
