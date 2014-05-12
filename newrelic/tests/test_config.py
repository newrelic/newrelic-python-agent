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

if __name__ == "__main__":
    unittest.main()
