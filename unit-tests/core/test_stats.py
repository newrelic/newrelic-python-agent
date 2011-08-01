'''
Created on Jul 25, 2011

@author: sdaubin
'''
from newrelic.core.stats import TimeStats
from newrelic.core.stats import ApdexStats
from newrelic.core.stats import StatsDict
from newrelic.core.config import create_configuration
from newrelic.core.metric import new_metric,Metric
from newrelic.core.remote import NRJSONEncoder
import unittest,collections,json

class ApdexStatsTest(unittest.TestCase):
    
    def test_record(self):
        apdex = create_configuration()
        s = ApdexStats(apdex)
        
        s.record(0.4)
        s.record(0.50)
        s.record(0.51)
        
        self.assertEqual(2, s.satisfying)
        self.assertEqual(1, s.tolerating)
        self.assertEqual(0, s.frustrating)
        
        s.record(2.0)
        s.record(2.01)
        
        self.assertEqual(2, s.tolerating)
        self.assertEqual(1, s.frustrating)

    def test_clone(self):
        apdex = create_configuration({"apdex_t":50})
        s = ApdexStats(apdex)
        s = s.clone()
        
        s.record(40)
        s.record(50)
        s.record(51)
        
        self.assertEqual(2, s.satisfying)
        self.assertEqual(1, s.tolerating)
        self.assertEqual(0, s.frustrating)
        
        s2 = s.clone()
        s2.record(75)
        
        self.assertEqual(2, s2.tolerating)
        self.assertEqual(1, s.tolerating)
        
    def test_merge(self):
        apdex = create_configuration({"apdex_t":50})
        s1 = ApdexStats(apdex)
        
        s1.record(40)
        s2 = s1.clone();
        
        s1.record(50)
        s1.record(51)
        
        s2.record(251)
        s2.record(88)
        s2.record(12)
        
        s1.merge(s2)
        
        self.assertEqual(4, s1.satisfying)
        self.assertEqual(2, s1.tolerating)
        self.assertEqual(1, s1.frustrating)

class TimeStatsTest(unittest.TestCase):


    def test_record(self):
        s = TimeStats()
        self.assertEqual(0,s.call_count)
        self.assertEqual(0,s.min_call_time)
        self.assertEqual(0,s.max_call_time)
        
        s.record(102,50)
        self.assertEqual(102,s.min_call_time)
        self.assertEqual(102,s.max_call_time)
        s.record(23,20)
        s.record(33,33)
        
        self.assertEqual(3,s.call_count)
        self.assertEqual(158,s.total_call_time)
        self.assertEqual(103,s.total_exclusive_call_time)
        self.assertEqual(23,s.min_call_time)
        self.assertEqual(102,s.max_call_time)

    def test_clone(self):
        s1 = TimeStats()
        s2 = s1.clone()
                
        self.assertEqual(0,s2.call_count)
        self.assertEqual(0,s2.total_call_time)
        
        s1.record(5,5)
        
        self.assertEqual(0,s2.call_count)
        self.assertEqual(0,s2.total_call_time)
        
        s2 = s1.clone()
        
        self.assertEqual(1,s2.call_count)
        self.assertEqual(5,s2.total_call_time)
        
        self.assertEqual(5,s2.total_exclusive_call_time)
        self.assertEqual(5,s2.min_call_time)
        self.assertEqual(5,s2.max_call_time)
        
    def test_merge(self):
        s1 = TimeStats()
        s1.record(5,5)
        s2 = s1.clone()
        s2.record(34,10)
                
        self.assertEqual(2,s2.call_count)
        self.assertEqual(39,s2.total_call_time)
        
        s1.merge(s2)
        
        self.assertEqual(3,s1.call_count)
        self.assertEqual(44,s1.total_call_time)
        
        self.assertEqual(20,s1.total_exclusive_call_time)
        self.assertEqual(5,s1.min_call_time)
        self.assertEqual(34,s1.max_call_time)  
        
    def test_json(self):
        s1 = TimeStats()
        s1.record(5,5)
        s1.record(33,30)
        
        s = json.dumps(s1,cls=NRJSONEncoder)
        self.assertEquals("[2, 38, 35, 5, 33, 1114]",s)
        
class StatsDictTest(unittest.TestCase):


    def test_get_apdex_stats(self):        
        d = StatsDict(create_configuration({"apdex_t":1}))
        s = d.get_apdex_stats("test")
        
        s.record(0.555)
        s.record(1.023)
        
        s2 = d.get_apdex_stats("test")
        self.assertEqual(s,s2)
        
    def test_metric_data(self):
        d = StatsDict(create_configuration({"apdex_t":1}))
        s = d.get_time_stats(new_metric("foo"))
        s.record(0.12,0.12)
        s = d.get_time_stats(new_metric("bar"))
        s.record(0.34,0.34)
        
        metric_ids = {}
        md = d.metric_data(metric_ids)
        self.assertEqual(2, len(md))
        
        self.assertEqual(new_metric("foo")._asdict(),md[0][0])
        self.assertEqual(new_metric("bar")._asdict(),md[1][0])
        
        s = json.dumps(md,cls=NRJSONEncoder)
        self.assertEqual("[[{\"name\": \"foo\", \"scope\": \"\"}, [1, 0.12, 0.12, 0.12, 0.12, 0.0144]], [{\"name\": \"bar\", \"scope\": \"\"}, [1, 0.34, 0.34, 0.34, 0.34, 0.11560000000000002]]]",s)
        
    def test_metric_data_with_ids(self):
        d = StatsDict(create_configuration({"apdex_t":1}))
        s = d.get_time_stats(Metric(u"foo",u""))
        s.record(0.12,0.12)
        
        metric_ids = {new_metric(u"foo"):12}
        md = d.metric_data(metric_ids)
        self.assertEqual(1, len(md))
        
        self.assertEqual(12,md[0][0])
                
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
