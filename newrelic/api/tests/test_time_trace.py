import unittest

import newrelic.tests.test_cases

from newrelic.api.time_trace import TimeTrace
from newrelic.core.attribute import MAX_NUM_USER_ATTRIBUTES


class SimpleNode(object):
    def __init__(self, is_async, start_time, end_time):
        self.is_async = is_async
        self.start_time = start_time
        self.end_time = end_time
        self.duration = self.end_time - self.start_time


class FakeSettings():
    def __init__(self, settings):
        for k, v in settings.items():
            setattr(self, k, v)


class FakeTransaction():
    def __init__(self, settings):
        self.settings = FakeSettings(settings)


class FakeRoot():
    def __init__(self, settings):
        self.transaction = FakeTransaction(settings)


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = False

    def setUp(self):
        super(TestCase, self).setUp()

        self.time_trace = TimeTrace(None)

        # model the existence of a sentinel
        self.time_trace.parent = TimeTrace(None)

    def test_add_agent_attribute(self):
        self.time_trace._add_agent_attribute('foo', 'bar')
        self.assertEqual(self.time_trace.agent_attributes['foo'], 'bar')

    def test_add_custom_attribute(self):
        self.time_trace.root = FakeRoot({'high_security': False})

        self.time_trace.add_custom_attribute('test', 'value')
        self.assertEqual(self.time_trace.user_attributes['test'], 'value')

    def test_add_custom_attribute_hsm_enabled(self):
        self.time_trace.root = FakeRoot({'high_security': True})

        self.time_trace.add_custom_attribute('test', 'value')
        self.assertFalse('test' in self.time_trace.user_attributes)

    def test_add_custom_attribute_attribute_limit(self):
        self.time_trace.root = FakeRoot({'high_security': False})

        for i in range(MAX_NUM_USER_ATTRIBUTES + 1):
            self.time_trace.add_custom_attribute('test_%i' % i, 'value')
        self.assertEqual(
                len(self.time_trace.user_attributes), MAX_NUM_USER_ATTRIBUTES)

    def test_sync_exclusive_calc(self):
        node_child_1 = SimpleNode(is_async=False, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=False, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1, node_child_1.is_async)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2, node_child_2.is_async)

        self.assertEqual(self.time_trace.exclusive, -1.5)

    def test_async_concurrent_children_exclusive_calc(self):
        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=1.5, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.increment_child_count()

        self.time_trace.process_child(node_child_1, node_child_1.is_async)
        self.time_trace.process_child(node_child_2, node_child_2.is_async)

        self.assertEqual(self.time_trace.exclusive, -1.5)

    def test_async_callback_children_exclusive_calc(self):
        self.time_trace.exited = True

        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1, node_child_1.is_async)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2, node_child_2.is_async)

        self.assertEqual(self.time_trace.exclusive, 0)

    def test_parent_child_overlap(self):
        self.time_trace.exited = True
        self.time_trace.exclusive = 1.5
        self.time_trace.end_time = 1.5

        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1, node_child_1.is_async)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2, node_child_2.is_async)

        self.assertEqual(self.time_trace.exclusive, 1.0)


if __name__ == '__main__':
    unittest.main()
