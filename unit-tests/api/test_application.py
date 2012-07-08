import unittest

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

class ApplicationTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_create(self):
        application = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertEqual(application.name, "UnitTests")

    def test_enabled(self):
        application = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertTrue(application.enabled)
        application.enabled = False
        self.assertFalse(application.enabled)
        application.enabled = True
        self.assertTrue(application.enabled)

    def test_singleton(self):
        application1 = newrelic.api.application.application_instance(
                "UnitTests")
        application2 = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertEqual(id(application1), id(application2))

if __name__ == '__main__':
    unittest.main()
