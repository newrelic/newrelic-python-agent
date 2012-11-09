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

if __name__ == "__main__":
    unittest.main()
