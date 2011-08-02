'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest,json
from newrelic.core.metric import Metric
from newrelic.core import metric 
from newrelic.core.remote import NRJSONEncoder

class TestMetric(unittest.TestCase):

    def test_default_scope(self):
        m1 = metric.new_metric(u"foo")
        m2 = metric.new_metric(u"foo")
        self.assertEqual(m1,m2)


    def test_equals(self):
        m1 = Metric(u"foo",u"")
        m2 = Metric(u"foo",u"")
        self.assertEqual(m1,m2)
        
    def test_not_equals(self):
        m1 = Metric(u"foo",u"")
        m2 = Metric(u"foo",u"bar")
        self.assertNotEqual(m1,m2)
        
    def test_dict_lookup(self):
        m1 = metric.new_metric(u"foo")
        d = {m1:True}
        m2 = metric.new_metric(u"foo")

        self.assertTrue(d[m2])
        
    def test_json(self):
        m = metric.new_metric(u"foo")
        s = json.dumps(m._asdict())
        self.assertEqual("{\"name\": \"foo\", \"scope\": \"\"}", s)
        print s

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()