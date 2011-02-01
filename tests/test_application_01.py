import unittest

import _newrelic

settings = _newrelic.Settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

class ApplicationTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_create(self):
        application = _newrelic.Application("UnitTests")
        self.assertEqual(application.name, "UnitTests")

    def test_enabled(self):
        application = _newrelic.Application("UnitTests")
        self.assertTrue(application.enabled)
        application.enabled = False
        self.assertFalse(application.enabled)
        application.enabled = True
        self.assertTrue(application.enabled)

    def test_singleton(self):
        application1 = _newrelic.Application("UnitTests")
        application2 = _newrelic.Application("UnitTests")
        self.assertEqual(id(application1), id(application2))

if __name__ == '__main__':
    unittest.main()
