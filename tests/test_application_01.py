import unittest

import _newrelic

class ApplicationTests01(unittest.TestCase):

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

    def test_harvest(self):
        application = _newrelic.Application("UnitTests")
        _newrelic.harvest()

if __name__ == '__main__':
    unittest.main()
