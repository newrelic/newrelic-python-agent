import unittest

from newrelic.samplers.memory_usage import memory_usage_data_source
from newrelic.samplers.data_sampler import DataSampler

class TestMemoryUsage(unittest.TestCase):

    def test_metrics(self):
        sampler = DataSampler('Unit Test', memory_usage_data_source,
                name=None, settings={})

        self.assertEqual(sampler.name, 'Memory Usage')

        sampler.start()

        metrics = dict(sampler.metrics())

        self.assertTrue('Memory/Physical' in metrics)

        self.assertTrue(metrics['Memory/Physical'] >= 0)

        sampler.stop()

if __name__ == '__main__':
    unittest.main()
