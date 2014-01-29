import unittest

import newrelic.core.config

class TestSettings(unittest.TestCase):

    def test_category_creation(self):
        d = { "a1": 1, "a2.b2": 2, "a3.b3.c3": 3 }
        c = newrelic.core.config.create_settings_snapshot(d)
        self.assertEqual(1, c.a1)
        self.assertEqual(2, c.a2.b2)
        self.assertEqual(3, c.a3.b3.c3)

class TestTransactionTracerConfig(unittest.TestCase):

    def test_defaults(self):
        c = newrelic.core.config.create_settings_snapshot()
        tt = c.transaction_tracer
        self.assertTrue(tt.enabled)
        self.assertEqual(None, tt.transaction_threshold)

    def test_enabled(self):
        d = { "transaction_tracer.enabled": False }
        c = newrelic.core.config.create_settings_snapshot(d)
        tt = c.transaction_tracer
        self.assertFalse(tt.enabled)

    def test_transaction_threshold(self):
        d = { "transaction_tracer.transaction_threshold": 0.666 }
        c = newrelic.core.config.create_settings_snapshot(d)
        tt = c.transaction_tracer
        self.assertEqual(0.666, tt.transaction_threshold)

class TestIgnoreStatusCodes(unittest.TestCase):

    def test_add_single(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes('100', values)
        self.assertEqual(values, set([100]))

    def test_add_single_many(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes('100 200', values)
        self.assertEqual(values, set([100, 200]))

    def test_add_range(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes('100-101', values)
        self.assertEqual(values, set([100, 101]))

    def test_add_range_many(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes('100-101 200-201',
                values)
        self.assertEqual(values, set([100, 101, 200, 201]))

    def test_add_range_length_one(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes('100-100', values)
        self.assertEqual(values, set([100]))

    def test_remove_single(self):
        values = set([100, 101, 102])
        newrelic.core.config.parse_ignore_status_codes('!101', values)
        self.assertEqual(values, set([100, 102]))

    def test_remove_single_many(self):
        values = set([100, 101, 102])
        newrelic.core.config.parse_ignore_status_codes('!101 !102', values)
        self.assertEqual(values, set([100]))

    def test_remove_range(self):
        values = set(range(100, 106))
        newrelic.core.config.parse_ignore_status_codes('!101-104', values)
        self.assertEqual(values, set([100,105]))

    def test_remove_range_many(self):
        values = set(range(100, 106))
        newrelic.core.config.parse_ignore_status_codes('!101-102 !103-104',
                values)
        self.assertEqual(values, set([100,105]))

    def test_remove_range_length_one(self):
        values = set([100, 101, 102])
        newrelic.core.config.parse_ignore_status_codes('!101-101', values)
        self.assertEqual(values, set([100, 102]))

    def test_add_and_remove(self):
        values = set()
        newrelic.core.config.parse_ignore_status_codes(
                '100-110 200 201 202 !201 !101-109', values)
        self.assertEqual(values, set([100, 110, 200, 202]))

if __name__ == "__main__":
    unittest.main()
