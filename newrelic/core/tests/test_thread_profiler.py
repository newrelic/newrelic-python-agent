import unittest
import zlib
import base64

from newrelic.core.thread_profiler import ThreadProfiler, ProfileNode, _MethodData

class TestThreadProfiler(unittest.TestCase):
    def setUp(self):
        self.profile_id = 42
        self.sample = 0.1
        self.duration = 2.0
        self.profile_agent_code = True
        self.tp = ThreadProfiler('Application', self.profile_id,
                self.sample, self.duration, self.profile_agent_code)
        self.tp.start_profiling()
        import time
        time.sleep(self.duration+self.sample)
        self.pd = self.tp.profile_data()

    def test_profiler(self):
        p = self.pd[0]
        self.assertEqual(p[0], self.profile_id)
        self.assertTrue(abs(self.duration-((p[2]-p[1])/1000)) < self.sample)
        self.assertEqual(p[3] , self.duration/self.sample)

    #def test_profile_data(self):
        #print self.pd
        #p = self.pd[0]
        #print zlib.decompress(base64.standard_b64decode(p[4]))
        #print ProfileNode.node_count

if __name__ == '__main__':
    unittest.main()
