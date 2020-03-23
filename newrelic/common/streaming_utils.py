import collections
import threading

try:
    from newrelic.core.mtb_pb2 import AttributeValue
except:
    AttributeValue = None


class StreamBuffer(object):
    CONNECTING = 0
    SENT_ONE = 1
    RUNNING = 2

    def __init__(self, maxlen):
        self._queue = collections.deque(maxlen=maxlen)
        self._notify = threading.Condition(threading.Lock())
        self._shutdown = False
        self._run_state = self.RUNNING

    def connect(self):
        self._run_state = self.CONNECTING

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

    def is_running(self):
        return self._run_state == self.RUNNING

    def _update_state(self):
        if self._run_state < self.RUNNING:
            self._run_state += 1

    def __next__(self):
        self._update_state()

        while True:
            if self._shutdown:
                raise StopIteration

            try:
                return self._queue.popleft()
            except IndexError:
                pass

            with self._notify:
                if not self._shutdown and not self._queue:
                    self._notify.wait()

    next = __next__

    def __iter__(self):
        return self


class SpanProtoAttrs(dict):
    def __init__(self, *args, **kwargs):
        super(SpanProtoAttrs, self).__init__()
        if args:
            arg = args[0]
            if len(args) > 1:
                raise TypeError(
                        "SpanProtoAttrs expected at most 1 argument, got %d",
                        len(args))
            elif hasattr(arg, 'keys'):
                for k in arg:
                    self[k] = arg[k]
            else:
                for k, v in arg:
                    self[k] = v

        for k in kwargs:
            self[k] = kwargs[k]

    def __setitem__(self, key, value):
        super(SpanProtoAttrs, self).__setitem__(key,
                SpanProtoAttrs.get_attribute_value(value))

    def copy(self):
        copy = SpanProtoAttrs()
        copy.update(self)
        return copy

    @staticmethod
    def get_attribute_value(value):
        if isinstance(value, bool):
            return AttributeValue(bool_value=value)
        elif isinstance(value, float):
            return AttributeValue(double_value=value)
        elif isinstance(value, int):
            return AttributeValue(int_value=value)
        else:
            return AttributeValue(string_value=str(value))
