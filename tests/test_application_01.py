import unittest

import _newrelic

class ApplicationTests01(unittest.TestCase):

    def test_create(self):
        application = _newrelic.Application("UnitTests")
        self.assertEqual(application.name, "UnitTests")
        self.assertTrue(application.enabled)
        application.enabled = False
        self.assertFalse(application.enabled)
        _newrelic.harvest()

if __name__ == '__main__':
    unittest.main()
