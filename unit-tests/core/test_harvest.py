'''
Created on Jul 28, 2011

@author: sdaubin
'''
import unittest
import time
import newrelic.core.harvest
from newrelic.core.harvest import start_harvest_thread, harvest_count,_harvest,\
    stop_harvest_thread, register_harvest_listener,clear_harvest_listeners

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
        stop_harvest_thread()
        clear_harvest_listeners()

    def test_stop_nonrunning_thread(self):
        self.assertFalse(stop_harvest_thread())

    def test_start_thread(self):
        self.assertEqual(0, harvest_count())
        try:
            self.assertTrue(start_harvest_thread(200))
            self.assertEqual(0, harvest_count())
        finally:
            self.assertTrue(stop_harvest_thread())
            
        self.assertEqual(0, harvest_count())

    def test_start_thread_and_harvest(self):
        # mock out the agent remote
        from newrelic.core.agent import newrelic_agent
        a = newrelic_agent()
        a._remote = MockRemote()
        
        self.assertEqual(0, harvest_count())
        l = HarvestListener()
        self.assertFalse(l.okay)        
        try:
            register_harvest_listener(l)
            self.assertTrue(start_harvest_thread(0.5))
            self.assertFalse(start_harvest_thread(200))
            self.assertEqual(0, harvest_count())
            time.sleep(2)
        finally:
            self.assertTrue(stop_harvest_thread())
            
        self.assertTrue(l.okay)
        self.assertTrue(harvest_count() > 0)
        
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()