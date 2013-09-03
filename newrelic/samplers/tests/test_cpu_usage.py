import unittest

from newrelic.samplers.cpu_usage import cpu_usage_data_source
from newrelic.samplers.data_sampler import DataSampler

def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)

class TestCPUUsage(unittest.TestCase):

    def test_metrics(self):
        sampler = DataSampler('Unit Test', cpu_usage_data_source,
                name=None, settings={})

        self.assertEqual(sampler.name, 'CPU Usage')

        sampler.start()

        fib(25)

        metrics = dict(sampler.metrics())

        self.assertTrue('CPU/User Time' in metrics)
        self.assertTrue('CPU/User/Utilization' in metrics)

        self.assertTrue(metrics['CPU/User Time'] >= 0)
        self.assertTrue(metrics['CPU/User/Utilization'] >= 0)

        sampler.stop()

if __name__ == '__main__':
    unittest.main()
