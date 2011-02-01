import unittest

import _newrelic

class HarvestTests01(unittest.TestCase):

    def test_harvest(self):
        _newrelic.harvest()

    def test_harvest_reason(self):
        _newrelic.harvest("shutdown")

    def test_harvest_application(self):
        application = _newrelic.Application("UnitTests")
        _newrelic.harvest()

if __name__ == '__main__':
    unittest.main()
