'''
Created on Jul 28, 2011

@author: sdaubin
'''
import unittest
import time
import newrelic.core.harvest
from newrelic.core.harvest import Harvester

class HarvestListener(object):
    def __init__(self):
        self._okay = False
    def get_okay(self):
        return self._okay
    def harvest(self,c):
        self._okay = True
    okay = property(get_okay, None, None, None)
    
class MockConnection(object):
    def close(self):
        pass
    
class MockRemote(object):
    def create_connection(self):
        return MockConnection()


class TestHarvest(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)


    def test_start_thread(self):
        h = Harvester(None, 200)
        try:
            self.assertEqual(0, h.harvest_count)
        finally:
            self.assertTrue(h.stop())
            
        self.assertEqual(0, h.harvest_count)

    def test_start_thread_and_harvest(self):
        l = HarvestListener()
        self.assertFalse(l.okay)
        h = Harvester(MockRemote(),0.5)
        try:
            h.register_harvest_listener(l)
            self.assertEqual(0, h.harvest_count)
            time.sleep(2)
        finally:
            self.assertTrue(h.stop())
            
        self.assertTrue(l.okay)
        self.assertTrue(h.harvest_count > 0)
        
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()