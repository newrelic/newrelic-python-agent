'''
Created on Jul 28, 2011

@author: sdaubin
'''
import unittest
import time
import newrelic.core.harvest
from newrelic.core.harvest import start_harvest_thread, harvest_count,_harvest,\
    stop_harvest_thread

class TestHarvest(unittest.TestCase):

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
        self.assertEqual(0, harvest_count())
        try:
            self.assertTrue(start_harvest_thread(0.5))
            self.assertFalse(start_harvest_thread(200))
            self.assertEqual(0, harvest_count())
            time.sleep(2)
        finally:
            self.assertTrue(stop_harvest_thread())
            
        self.assertTrue(harvest_count() > 0)
        
    def test_harvest(self):
        _harvest()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()