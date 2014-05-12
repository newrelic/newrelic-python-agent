import copy
import unittest

import newrelic.config

class TestHighSecurityMode(unittest.TestCase):

    def setUp(self):
        self.original_settings = copy.deepcopy(newrelic.config._settings)
        self.settings = newrelic.config._settings

    def tearDown(self):
        newrelic.config._settings = self.original_settings

    def test_hsm_default(self):
        self.assertFalse(self.settings.high_security)

if __name__ == "__main__":
    unittest.main()
