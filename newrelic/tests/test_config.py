import copy
import unittest

import newrelic.config

class TestProcessHighSecurityMode(unittest.TestCase):

    def setUp(self):
        self.original_settings = copy.deepcopy(newrelic.config._settings)
        self.settings = newrelic.config._settings

    def tearDown(self):
        newrelic.config._settings = self.original_settings

    def test_hsm_default(self):
        self.assertFalse(self.settings.high_security)

    def test_hsm_on_ssl_enabled(self):
        self.settings.high_security = True
        newrelic.config._process_high_security_mode()
        self.assertTrue(self.settings.ssl)

    def test_hsm_on_ssl_disabled(self):
        self.settings.high_security = True
        self.settings.ssl = False
        newrelic.config._process_high_security_mode()
        self.assertTrue(self.settings.ssl)

    def test_hsm_on_config_params_disabled(self):
        self.settings.high_security = True
        newrelic.config._process_high_security_mode()
        self.assertFalse(self.settings.capture_params)

    def test_hsm_on_config_params_enabled(self):
        self.settings.high_security = True
        self.settings.capture_params = True
        newrelic.config._process_high_security_mode()
        self.assertFalse(self.settings.capture_params)

    def test_hsm_on_record_sql_obfuscated(self):
        self.settings.high_security = True
        newrelic.config._process_high_security_mode()
        record_sql = self.settings.transaction_tracer.record_sql
        self.assertEqual(record_sql, 'obfuscated')

    def test_hsm_on_record_sql_off(self):
        self.settings.high_security = True
        self.settings.transaction_tracer.record_sql = 'off'
        newrelic.config._process_high_security_mode()
        record_sql = self.settings.transaction_tracer.record_sql
        self.assertEqual(record_sql, 'off')

    def test_hsm_on_record_sql_raw(self):
        self.settings.high_security = True
        self.settings.transaction_tracer.record_sql = 'raw'
        newrelic.config._process_high_security_mode()
        record_sql = self.settings.transaction_tracer.record_sql
        self.assertEqual(record_sql, 'obfuscated')

if __name__ == "__main__":
    unittest.main()
