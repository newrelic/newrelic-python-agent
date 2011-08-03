'''
Created on Jul 28, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.config import create_settings_snapshot

class TestAgentConfig(unittest.TestCase):

    def test_defaults(self):
        c = create_settings_snapshot()
        self.assertTrue(0.5,c.apdex_t)
        self.assertTrue(2.0,c.apdex_f)
        

    def test_apdex_t(self):
        c = create_settings_snapshot({"apdex_t":0.666})
        self.assertTrue(0.666,c.apdex_t)
        self.assertTrue(0.666*4,c.apdex_f)


class TestTransactionTracerConfig(unittest.TestCase):

    def test_defaults(self):
        tt = create_settings_snapshot().transaction_tracer
        self.assertTrue(tt.enabled)
        self.assertEqual(2,tt.transaction_threshold)
        

    def test_enabled(self):
        tt = create_settings_snapshot({"transaction_tracer.enabled":False}).transaction_tracer        
        self.assertFalse(tt.enabled)

    def test_transaction_threshold(self):
        tt = create_settings_snapshot({"transaction_tracer.transaction_threshold":0.666}).transaction_tracer        
        self.assertEqual(0.666,tt.transaction_threshold)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
