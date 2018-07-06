import newrelic.tests.test_cases
from newrelic.core.adaptive_sampler import AdaptiveSampler


class TestAdaptiveSampler(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        super(TestAdaptiveSampler, self).setUp()

        self.target = 10
        self.adaptive_sampler = AdaptiveSampler(self.target)

    def test_sampling_probability_first_harvest(self):
        for _ in range(self.target):
            assert self.adaptive_sampler.compute_sampled(0.0) is True

        assert self.adaptive_sampler.compute_sampled(1.0) is False
        self.assertEqual(self.adaptive_sampler.sampled_count, self.target)

    def test_sampling_probability_after_harvest(self):
        self.adaptive_sampler.reset(0)
        max_sampled = 2 * self.target

        for _ in range(max_sampled):
            assert self.adaptive_sampler.compute_sampled(1.0) is True

        assert self.adaptive_sampler.compute_sampled(1.0) is False
        self.assertEqual(self.adaptive_sampler.sampled_count, max_sampled)

    def test_sampling_probability_not_sampled(self):
        # sets min_sampling_priority to 1.0
        self.adaptive_sampler.reset(float('inf'))

        assert self.adaptive_sampler.compute_sampled(0.99) is False

    def test_sampling_probability_count_above_target(self):
        count = 2 * self.target

        expected_min_sampling_priority = (1.0 - float(self.target) / count)

        self.adaptive_sampler.reset(count)
        assert self.adaptive_sampler.compute_sampled(
                expected_min_sampling_priority) is True
        assert self.adaptive_sampler.compute_sampled(
                expected_min_sampling_priority - 0.01) is False

    def test_sampling_probability_count_below_target(self):
        self.adaptive_sampler.reset(1)

        assert self.adaptive_sampler.compute_sampled(0) is True

    def test_exponential_backoff(self):
        self.adaptive_sampler.reset(100)

        expected_min_priority = [
            0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
            0.9505096935227151, 0.9634935696958876, 0.9728426158789346,
            0.9798280298093717, 0.9852068882655560, 0.9894531262588255,
            0.9928760253971225, 0.9956846399636375, 0.998024593738846
        ]

        for sample_num in range(20):
            self.assertAlmostEqual(
                    self.adaptive_sampler.min_sampling_priority,
                    expected_min_priority[sample_num])

            self.adaptive_sampler.compute_sampled(1.0)

    def test_target_zero(self):
        self.adaptive_sampler = AdaptiveSampler(0)

        assert self.adaptive_sampler.compute_sampled(1.0) is False

        self.adaptive_sampler.reset(0)

        assert self.adaptive_sampler.compute_sampled(1.0) is False
