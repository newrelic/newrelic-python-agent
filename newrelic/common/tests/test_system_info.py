import unittest

from newrelic.common.system_info import cpu_count, memory_total, memory_used

class TestCpuCount(unittest.TestCase):

    def test_cpu_count(self):
        self.assertTrue(cpu_count() >= 1)

class TestSystemMemory(unittest.TestCase):

    def test_memory_total(self):
        self.assertTrue(memory_total() >= 0)

    def test_memory_used(self):
        self.assertTrue(memory_used() >= 0)

        if memory_total() > 0:
            self.assertTrue(memory_used() <= memory_total())

if __name__ == '__main__':
    unittest.main()
