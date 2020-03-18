import collections
import threading


class TerminatingDeque(object):
    def __init__(self, maxlen):
        self._queue = collections.deque(maxlen=maxlen)
        self._notify = threading.Condition(threading.Lock())
        self._shutdown = False

    def shutdown(self):
        with self._notify:
            self._shutdown = True
            self._notify.notify_all()

    def put(self, item):
        with self._notify:
            if self._shutdown:
                return

            self._queue.append(item)
            self._notify.notify_all()

    def __next__(self):
        if self._queue:
            return self._queue.popleft()

        with self._notify:
            while not self._queue:
                if self._shutdown:
                    raise StopIteration
                self._notify.wait()

        return self._queue.popleft()

    next = __next__

    def __iter__(self):
        return self
