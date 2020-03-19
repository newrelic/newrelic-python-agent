import collections
import threading

try:
    from newrelic.core.mtb_pb2 import AttributeValue
except:
    pass


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


class SpanProtoAttrs(dict):
    def __init__(self, values=(), **kwargs):
        for k, v in values:
            self[k] = v

    def __setitem__(self, key, value):
        super(SpanProtoAttrs, self).__setitem__(key,
                SpanProtoAttrs.get_attribute_value(value))

    def copy(self):
        copy = SpanProtoAttrs()
        copy.update(self)
        return copy

    @staticmethod
    def get_attribute_value(value):
        if isinstance(value, float):
            return AttributeValue(double_value=value)
        elif isinstance(value, int):
            return AttributeValue(int_value=value)
        elif isinstance(value, bool):
            return AttributeValue(bool_value=value)
        else:
            return AttributeValue(string_value=str(value))
