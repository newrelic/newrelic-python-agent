import unittest

from newrelic.core.thread_profiler import ProfileNode, _MethodData

class TestProfileNode(unittest.TestCase):
    def setUp(self):
        self.f = [_MethodData('file%d'%(i), 'func%d'%(i), i) for i in range(10)]
        self.call_tree = ProfileNode(self.f[0])

    def test_get_child(self):
        child = self.call_tree.get_or_create_child(self.f[0])
        self.assertEqual(child.method, self.f[0])
        self.assertEqual(child.call_count, 0)

    def test_create_child(self):
        child = self.call_tree.get_or_create_child(self.f[1])
        self.assertEqual(child.method, self.f[1])
        self.assertEqual(child.call_count, 0)

    def test_increment_call_count(self):
        child = self.call_tree.get_or_create_child(self.f[0])
        child.increment_call_count()
        self.assertEqual(child.call_count, 1)

    def test_jsonable(self):
        self.call_tree.increment_call_count()
        self.assertEqual(self.call_tree.jsonable(), [self.f[0], 1, 0, []])

if __name__ == '__main__':
    unittest.main()
