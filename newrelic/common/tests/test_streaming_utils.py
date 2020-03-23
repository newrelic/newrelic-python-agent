import threading
import newrelic.tests.test_cases
import newrelic.common.streaming_utils as streaming_utils


class TestTerminatingDeque(newrelic.tests.test_cases.TestCase):
    def setUp(self):
        self.terminating_deque = streaming_utils.TerminatingDeque(2)
        self.lock = self.terminating_deque._notify

    def test_simple_put(self):
        item = object()

        # Set up a put operation on a separate thread
        thread = threading.Thread(
                target=self.terminating_deque.put, args=(item,))
        thread.daemon = True

        with self.lock:
            thread.start()

            # The lock should prevent the item from being added to the queue
            assert len(self.terminating_deque._queue) == 0

        # The thread should terminate after the lock is released
        thread.join(timeout=0.1)
        assert not thread.is_alive()

        # The item should be added to the queue
        assert len(self.terminating_deque._queue) == 1

    def test_shutdown_prevents_additional_puts(self):
        item = object()

        # Call shutdown
        self.terminating_deque.shutdown()

        # Attempt to put item into the deque
        self.terminating_deque.put(item)

        # The item should not be in the queue
        assert len(self.terminating_deque._queue) == 0

    def test_shutdown_terminates_iterator(self):
        # Set up an iterator thread
        thread = threading.Thread(
                target=lambda: [_ for _ in self.terminating_deque])
        thread.daemon = True

        # Force the thread to start
        thread.start()
        assert thread.is_alive()

        # Call shutdown
        self.terminating_deque.shutdown()

        # Thread terminates immediately
        thread.join(timeout=0.1)
        assert not thread.is_alive()

    def test_queue_drains_before_shutdown(self):
        items = [object() for _ in range(2)]

        # Put items into the queue and shutdown
        for item in items:
            self.terminating_deque.put(item)
        self.terminating_deque.shutdown()

        # Set up consumer to record items consumed in a background thread
        consumed = []
        thread = threading.Thread(
                target=lambda: consumed.extend(
                    item for item in self.terminating_deque))
        thread.daemon = True
        thread.start()

        # The thread should shut down only after consuming
        thread.join(timeout=0.1)
        assert not thread.is_alive()
        assert consumed == items


class AttributeValue(object):
    def __init__(self, *args, **kwargs):
        if args:
            raise TypeError("args not allowed")
        elif len(kwargs) != 1:
            raise TypeError("exactly 1 keyword argument must be specified")
        k, v = list(kwargs.items())[0]
        setattr(self, k, v)


class TestSpanProtoAttrs(newrelic.tests.test_cases.TestCase):
    def setUp(self):
        self.restore = streaming_utils.AttributeValue
        streaming_utils.AttributeValue = AttributeValue

    def tearDown(self):
        streaming_utils.AttributeValue = self.restore

    def test_get_attribute_value_bool(self):
        value = streaming_utils.SpanProtoAttrs.get_attribute_value(True)
        assert value.bool_value is True

    def test_get_attribute_value_int(self):
        value = streaming_utils.SpanProtoAttrs.get_attribute_value(9000)
        assert value.int_value == 9000

    def test_get_attribute_value_float(self):
        value = streaming_utils.SpanProtoAttrs.get_attribute_value(9000.0)
        assert value.double_value == 9000.0

    def test_get_attribute_value_str(self):
        value = streaming_utils.SpanProtoAttrs.get_attribute_value("hi")
        assert value.string_value == "hi"
