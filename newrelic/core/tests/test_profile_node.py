import unittest

from newrelic.core.thread_profiler import ProfileNode, _MethodData

class TestProfileNode(unittest.TestCase):
    def setUp(self):
        self.f = [_MethodData('file%d'%(i), 'func%d'%(i), i) for i in range(10)]
        self.call_tree = ProfileNode(self.f[0])

    def test_jsonable(self):
        self.assertEqual(self.call_tree.jsonable(), [self.f[0], 0, 0, []])

if __name__ == '__main__':
    unittest.main()
