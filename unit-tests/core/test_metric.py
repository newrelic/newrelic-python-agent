'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.metric import Metric
from newrelic.core import metric 

class TestMetric(unittest.TestCase):

    def test_default_scope(self):
        m1 = metric.new_metric("foo")
        m2 = metric.new_metric("foo")
        self.assertEqual(m1,m2)


    def test_equals(self):
        m1 = Metric("foo","")
        m2 = Metric("foo","")
        self.assertEqual(m1,m2)
        
    def test_not_equals(self):
        m1 = Metric("foo","")
        m2 = Metric("foo","bar")
        self.assertNotEqual(m1,m2)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()