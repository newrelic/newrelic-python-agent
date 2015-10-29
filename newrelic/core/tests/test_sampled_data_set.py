import unittest

from newrelic.core.stats_engine import SampledDataSet

class TestSampledDataSet(unittest.TestCase):

    def test_empty_set(self):
        instance = SampledDataSet()

        self.assertEqual(instance.samples, [])
        self.assertEqual(instance.capacity, 100)
        self.assertEqual(instance.count, 0)

    def test_single_item(self):
        instance = SampledDataSet()

        instance.add(1)

        self.assertEqual(instance.samples, [1])
        self.assertEqual(instance.count, 1)

    def test_at_capacity(self):
        instance = SampledDataSet(100)

        for i in range(100):
            instance.add(i)

        self.assertEqual(len(instance.samples), 100)
        self.assertEqual(sorted(instance.samples), list(range(100)))
        self.assertEqual(instance.count, 100)

    def test_over_capacity(self):
        instance = SampledDataSet(100)

        for i in range(200):
            instance.add(i)

        self.assertEqual(len(instance.samples), 100)
        self.assertEqual(instance.count, 200)

    def test_merge_sampled_data_set_under_capacity(self):
        a = SampledDataSet(capacity=100)
        b = SampledDataSet(capacity=100)

        count_a = 10
        count_b = 12
        for i in range(count_a):
            a.add(i)

        for i in range(count_b):
            b.add(i)

        a.merge(b)

        self.assertEqual(a.count, count_a + count_b)
        self.assertEqual(a.count, len(a.samples))

    def test_merge_sampled_data_set_over_capacity(self):
        capacity = 100
        a = SampledDataSet(capacity=capacity)
        b = SampledDataSet(capacity=capacity)

        count_a = 110
        count_b = 200
        for i in range(count_a):
            a.add(i)

        for i in range(count_b):
            b.add(i)

        a.merge(b)

        self.assertEqual(a.count, count_a + count_b)
        self.assertEqual(len(a.samples), capacity)

if __name__ == '__main__':
    unittest.main()
