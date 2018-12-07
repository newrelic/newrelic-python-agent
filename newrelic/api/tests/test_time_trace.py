import unittest

import newrelic.tests.test_cases

from newrelic.api.time_trace import TimeTrace


class SimpleNode(object):
    def __init__(self, is_async, start_time, end_time):
        self.is_async = is_async
        self.start_time = start_time
        self.end_time = end_time
        self.duration = self.end_time - self.start_time


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

    def test_sync_exclusive_calc(self):
        node_child_1 = SimpleNode(is_async=False, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=False, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2)

        self.assertEqual(self.time_trace.exclusive, -1.5)

    def test_async_concurrent_children_exclusive_calc(self):
        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=1.5, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.increment_child_count()

        self.time_trace.process_child(node_child_1)
        self.time_trace.process_child(node_child_2)

        self.assertEqual(self.time_trace.exclusive, -1.5)

    def test_async_callback_children_exclusive_calc(self):
        self.time_trace.exited = True

        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2)

        self.assertEqual(self.time_trace.exclusive, 0)

    def test_parent_child_overlap(self):
        self.time_trace.exited = True
        self.time_trace.exclusive = 1.5
        self.time_trace.end_time = 1.5

        node_child_1 = SimpleNode(is_async=True, start_time=1.0, end_time=2.0)
        node_child_2 = SimpleNode(is_async=True, start_time=2.0, end_time=2.5)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_1)

        self.time_trace.increment_child_count()
        self.time_trace.process_child(node_child_2)

        self.assertEqual(self.time_trace.exclusive, 1.0)


if __name__ == '__main__':
    unittest.main()
