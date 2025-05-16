import utime
import sys
import _thread
import osTimer


class Lock(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__owner = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self):
        flag = self.__lock.acquire()
        self.__owner = _thread.get_ident()
        return flag

    def release(self):
        self.__owner = None
        return self.__lock.release()

    def locked(self):
        return self.__lock.locked()

    @property
    def owner(self):
        return self.__owner


class _Waiter(object):
    """WARNING: Waiter object can only be used once."""

    def __init__(self):
        self.__lock = Lock()
        self.__lock.acquire()
        self.__gotit = True

    @property
    def __unlock_timer(self):
        timer = getattr(self, '__unlock_timer__', None)
        if timer is None:
            timer = osTimer()
            setattr(self, '__unlock_timer__', timer)
        return timer

    @property
    def __timer_lock(self):
        lock = getattr(self, '__timer_lock__', None)
        if lock is None:
            lock = Lock()
            setattr(self, '__timer_lock__', lock)
        return lock

    def __auto_release(self, _):
        with self.__timer_lock:
            self.__gotit = not self.__release()

    def acquire(self, timeout=None):
        if timeout is not None and timeout <= 0:
            raise ValueError("'timeout' must be a positive number.")
        gotit = self.__gotit
        if timeout:
            with self.__timer_lock:
                self.__unlock_timer.start(timeout * 1000, 0, self.__auto_release)
        self.__lock.acquire()  # block here
        if timeout:
            with self.__timer_lock:
                gotit = self.__gotit
            self.__unlock_timer.stop()
        return gotit

    def __release(self):
        try:
            self.__lock.release()
        except RuntimeError:
            return False
        return True

    def release(self):
        return self.__release()


class Condition(object):

    def __init__(self, lock=None):
        if lock is None:
            lock = Lock()
        self.__lock = lock
        self.__waiters = []
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs):
        self.release()

    def __is_owned(self):
        return self.__lock.locked() and self.__lock.owner == _thread.get_ident()

    def wait(self, timeout=None):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        waiter = _Waiter()
        self.__waiters.append(waiter)
        self.release()
        gotit = False
        try:
            gotit = waiter.acquire(timeout)
            return gotit
        finally:
            self.acquire()
            if not gotit:
                try:
                    self.__waiters.remove(waiter)
                except ValueError:
                    pass

    def wait_for(self, predicate, timeout=None):
        endtime = None
        remaining = timeout
        result = predicate()
        while not result:
            if remaining is not None:
                if endtime is None:
                    endtime = utime.time() + remaining
                else:
                    remaining = endtime - utime.time()
                    if remaining <= 0.0:
                        break
            self.wait(remaining)
            result = predicate()
        return result

    def notify(self, n=1):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        if n < 0:
            raise ValueError('invalid param, n should be >= 0.')
        waiters_to_notify = self.__waiters[:n]
        for waiter in waiters_to_notify:
            waiter.release()
            try:
                self.__waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        self.notify(n=len(self.__waiters))


class Event(object):

    def __init__(self):
        self.__flag = False
        self.__cond = Condition()

    def wait(self, timeout=None, clear=False):
        with self.__cond:
            result = self.__cond.wait_for(lambda: self.__flag, timeout=timeout)
            if result and clear:
                self.__flag = False
            return result

    def set(self):
        with self.__cond:
            self.__flag = True
            self.__cond.notify_all()

    def clear(self):
        with self.__cond:
            self.__flag = False

    def is_set(self):
        with self.__cond:
            return self.__flag


class EventSet(object):

    def __init__(self):
        self.__set = 0
        self.__cond = Condition()
    
    def wait(self, event_set, timeout=None, clear=False):
        with self.__cond:
            result = self.__cond.wait_for(lambda: (event_set & self.__set) == event_set, timeout=timeout)
            if result and clear:
                self.__set &= ~event_set
            return result
    
    def wait_any(self, event_set, timeout=None, clear=False):
        with self.__cond:
            result = self.__cond.wait_for(lambda: event_set & self.__set, timeout=timeout)
            if result and clear:
                self.__set &= ~event_set
            return result
    
    def set(self, event_set):
        with self.__cond:
            self.__set |= event_set
            self.__cond.notify_all()

    def clear(self, event_set):
        with self.__cond:
            self.__set &= ~event_set
    
    def is_set(self, event_set):
        with self.__cond:
            return (self.__set & event_set) == event_set
    
    def is_set_any(self, event_set):
        with self.__cond:
            return self.__set & event_set


class Semaphore(object):

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self.__value = value
        self.__cond = Condition()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs):
        self.release()

    def counts(self):
        with self.__cond:
            return self.__value

    def acquire(self, block=True, timeout=None):
        with self.__cond:
            if not block:
                if self.__value > 0:
                    self.__value -= 1
                    return True
                else:
                    return False
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if self.__cond.wait_for(lambda: self.__value > 0, timeout=timeout):
                    self.__value -= 1
                    return True
                else:
                    return False

    def release(self, n=1):
        if n < 1:
            raise ValueError('n must be one or more')
        with self.__cond:
            self.__value += n
            self.__cond.notify(n)

    def clear(self):
        with self.__cond:
            self.__value = 0


class BoundedSemaphore(Semaphore):

    def __init__(self, value=1):
        super().__init__(value)
        self.__initial_value = value

    def release(self, n=1):
        if n < 1:
            raise ValueError('n must be one or more')
        with self.__cond:
            if self.__value + n > self.__initial_value:
                raise ValueError("Semaphore released too many times")
            self.__value += n
            self.__cond.notify(n)


class Queue(object):
    class Full(Exception):
        pass

    class Empty(Exception):
        pass

    def __init__(self, max_size=100):
        self.queue = []
        self.__max_size = max_size
        self.__lock = Lock()
        self.__not_empty = Condition(self.__lock)
        self.__not_full = Condition(self.__lock)

    def _put(self, item):
        self.queue.append(item)

    def put(self, item, block=True, timeout=None):
        with self.__not_full:
            if not block:
                if len(self.queue) >= self.__max_size:
                    raise self.Full
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_full.wait_for(lambda: len(self.queue) < self.__max_size, timeout=timeout):
                    raise self.Full
            self._put(item)
            self.__not_empty.notify()

    def _get(self):
        return self.queue.pop(0)

    def get(self, block=True, timeout=None):
        with self.__not_empty:
            if not block:
                if len(self.queue) == 0:
                    raise self.Empty
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_empty.wait_for(lambda: len(self.queue) != 0, timeout=timeout):
                    raise self.Empty
            item = self._get()
            self.__not_full.notify()
            return item

    def size(self):
        with self.__lock:
            return len(self.queue)

    def clear(self):
        with self.__lock:
            self.queue.clear()


class LifoQueue(Queue):

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()


class PriorityQueue(Queue):

    @classmethod
    def __siftdown(cls, heap, startpos, pos):
        newitem = heap[pos]
        while pos > startpos:
            parentpos = (pos - 1) >> 1
            parent = heap[parentpos]
            if newitem < parent:
                heap[pos] = parent
                pos = parentpos
                continue
            break
        heap[pos] = newitem

    def _put(self, item):
        self.queue.append(item)
        self.__siftdown(self.queue, 0, len(self.queue) - 1)

    @classmethod
    def __siftup(cls, heap, pos):
        endpos = len(heap)
        startpos = pos
        newitem = heap[pos]
        childpos = 2 * pos + 1
        while childpos < endpos:
            rightpos = childpos + 1
            if rightpos < endpos and not heap[childpos] < heap[rightpos]:
                childpos = rightpos
            heap[pos] = heap[childpos]
            pos = childpos
            childpos = 2 * pos + 1
        heap[pos] = newitem
        cls.__siftdown(heap, startpos, pos)

    def _get(self):
        lastelt = self.queue.pop()
        if self.queue:
            returnitem = self.queue[0]
            self.queue[0] = lastelt
            self.__siftup(self.queue, 0)
            return returnitem
        return lastelt


class Thread(object):
    DEFAULT_STACK_SIZE = _thread.stack_size()

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.__ident = None
        self.__stopped_event = Event()

    def is_running(self):
        if self.__ident is None:
            return False
        else:
            return _thread.threadIsRunning(self.__ident)

    def join(self, timeout=None):
        return self.__stopped_event.wait(timeout=timeout)

    def terminate(self):
        """WARNING: you must release all resources after terminate thread, especially **Lock(s)**"""
        if self.is_running():
            _thread.stop_thread(self.ident)
            self.__ident = None
        self.__stopped_event.set()

    def start(self, stack_size=None):
        if self.__ident is not None:
            raise RuntimeError("threads can only be started once")
        if stack_size is not None:
            _thread.stack_size(stack_size * 1024)
        self.__ident = _thread.start_new_thread(self.__bootstrap, ())
        if stack_size is not None:
            _thread.stack_size(self.DEFAULT_STACK_SIZE)

    def __bootstrap(self):
        try:
            self.run()
        except Exception as e:
            sys.print_exception(e)
        finally:
            self.__stopped_event.set()

    def run(self):
        if self.__target:
            self.__target(*self.__args, **self.__kwargs)

    @property
    def ident(self):
        return self.__ident


class _Result(object):
    class TimeoutError(Exception):
        pass

    class NotReadyError(Exception):
        pass

    def __init__(self):
        self.__rv = None
        self.__exc = None
        self.__finished = Event()

    def set(self, exc=None, rv=None):
        self.__exc = exc
        self.__rv = rv
        self.__finished.set()

    def __get_value_or_raise_exc(self):
        if self.__exc:
            raise self.__exc
        return self.__rv

    def get(self, block=True, timeout=None):
        if not block:
            if self.__finished.is_set():
                return self.__get_value_or_raise_exc()
            raise self.NotReadyError('result not ready')
        if self.__finished.wait(timeout=timeout):
            return self.__get_value_or_raise_exc()
        else:
            raise self.TimeoutError('get result timeout.')


class AsyncTask(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}

    def delay(self, seconds=None):
        result = _Result()
        Thread(target=self.__run, args=(result, seconds)).start()
        return result

    def __run(self, result, delay_seconds):
        if delay_seconds is not None and delay_seconds > 0:
            utime.sleep(delay_seconds)
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            sys.print_exception(e)
            result.set(exc=e)
        else:
            result.set(rv=rv)

    @classmethod
    def wrapper(cls, func):
        def inner_wrapper(*args, **kwargs):
            return cls(target=func, args=args, kwargs=kwargs)
        return inner_wrapper


class _WorkItem(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.result = _Result()

    def __call__(self, *args, **kwargs):
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            self.result.set(exc=e)
        else:
            self.result.set(rv=rv)


def _worker(work_queue):
    while True:
        try:
            task = work_queue.get()
            task()
        except Exception as e:
            sys.print_exception(e)


class ThreadPoolExecutor(object):

    def __init__(self, max_workers=4):
        if max_workers <= 0:
            raise ValueError('max_workers must be greater than 0.')
        self.__max_workers = max_workers
        self.__work_queue = Queue()
        self.__threads = set()
        self.__lock = Lock()

    def submit(self, *args, **kwargs):
        with self.__lock:
            item = _WorkItem(*args, **kwargs)
            self.__work_queue.put(item)
            self.__adjust_thread_count()
            return item.result

    def __adjust_thread_count(self):
        if len(self.__threads) < self.__max_workers:
            t = Thread(target=_worker, args=(self.__work_queue,))
            t.start()
            self.__threads.add(t)

    def shutdown(self):
        with self.__lock:
            for t in self.__threads:
                t.terminate()
            self.__threads = set()
            self.__work_queue = Queue()
