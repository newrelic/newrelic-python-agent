import unittest
import zlib
import base64

from newrelic.core.thread_profiler import ThreadProfiler, ProfileNode, _MethodData

class TestThreadProfiler(unittest.TestCase):
    def setUp(self):
        self.profile_id = 42
        self.sample = 0.1
        self.duration = 0.2
        self.profile_agent_code = True
        self.tp = ThreadProfiler(self.profile_id, self.sample, self.duration,
                self.profile_agent_code)

    def test_profiler(self):
        self.tp.start_profiling()
        import time
        time.sleep(0.3)
        pd = self.tp.profile_data()
        p = pd[0]
        self.assertEqual(p[0], self.profile_id)
        self.assertGreaterEqual(p[2] - p[1], self.duration) 
        self.assertEqual(p[3] , self.duration/self.sample)
        #print pd
        #print zlib.decompress(base64.standard_b64decode(p[4]))

if __name__ == '__main__':
    unittest.main()
