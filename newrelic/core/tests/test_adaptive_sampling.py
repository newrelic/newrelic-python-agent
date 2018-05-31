import newrelic.tests.test_cases
from newrelic.core.adaptive_sampling import AdaptiveSampling


class TestAdaptiveSampling(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        super(TestAdaptiveSampling, self).setUp()

        self.target = 10
        self.adaptive_sampling = AdaptiveSampling(self.target)

    def test_sampling_probability_first_harvest(self):
        for _ in range(self.target):
            assert self.adaptive_sampling.compute_sampled(0.0) is True

        assert self.adaptive_sampling.compute_sampled(1.0) is False
        self.assertEqual(self.adaptive_sampling.sampled_count, self.target)

    def test_sampling_probability_after_harvest(self):
        self.adaptive_sampling.reset(0)
        max_sampled = 2 * self.target

        for _ in range(max_sampled):
            assert self.adaptive_sampling.compute_sampled(1.0) is True

        assert self.adaptive_sampling.compute_sampled(1.0) is False
        self.assertEqual(self.adaptive_sampling.sampled_count, max_sampled)

    def test_sampling_probability_not_sampled(self):
        # sets min_sampling_priority to 1.0
        self.adaptive_sampling.reset(float('inf'))

        assert self.adaptive_sampling.compute_sampled(0.99) is False

    def test_sampling_probability_count_above_target(self):
        count = 2 * self.target

        expected_min_sampling_priority = (1.0 - float(self.target) / count)

        self.adaptive_sampling.reset(count)
        assert self.adaptive_sampling.compute_sampled(
                expected_min_sampling_priority) is True
        assert self.adaptive_sampling.compute_sampled(
                expected_min_sampling_priority - 0.01) is False

    def test_sampling_probability_count_below_target(self):
        self.adaptive_sampling.reset(1)

        assert self.adaptive_sampling.compute_sampled(0) is True

    def test_exponential_backoff(self):
        self.adaptive_sampling.reset(100)

        expected_min_priority = [
            0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
            0.9512462826139941, 0.9642301587871667, 0.9735792049702137,
            0.9805646189006507, 0.9859434773568351, 0.9901897153501046,
            0.9936126144884015, 0.9964212290549166, 0.998761182830125
        ]

        for sample_num in range(20):
            self.assertAlmostEqual(
                    self.adaptive_sampling.min_sampling_priority,
                    expected_min_priority[sample_num])

            self.adaptive_sampling.compute_sampled(1.0)
