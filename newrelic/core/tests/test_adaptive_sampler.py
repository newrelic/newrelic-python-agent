import random
import newrelic.tests.test_cases
from newrelic.core.adaptive_sampler import AdaptiveSampler


def bind_randrange(*args, **kwargs):
    def _bind_a(stop):
        return stop

    def _bind_b(start, stop, step):
        return stop

    try:
        return _bind_a(*args, **kwargs)
    except:
        return _bind_b(*args, **kwargs)


class TestAdaptiveSampler(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        super(TestAdaptiveSampler, self).setUp()

        self.original_randrange = random.randrange
        self.value = float('inf')

        self.target = 10
        self.adaptive_sampler = AdaptiveSampler(self.target, 60.0)

    def tearDown(self):
        self.unpatch()

    def patch(self):
        def _randrange(*args, **kwargs):
            stop = bind_randrange(*args, **kwargs)
            assert stop > self.value, "Illegal randrange value"
            return self.value
        random.randrange = _randrange

    def unpatch(self):
        random.randrange = self.original_randrange

    def test_sampling_probability_first_harvest(self):
        for _ in range(self.target):
            assert self.adaptive_sampler.compute_sampled() is True

        assert self.adaptive_sampler.compute_sampled() is False

        self.assertEqual(self.adaptive_sampler.sampled_count, self.target)

    def test_sampling_probability_after_harvest(self):
        self.adaptive_sampler.reset()
        max_sampled = 2 * self.target

        self.value = 0
        self.patch()

        for _ in range(max_sampled):
            assert self.adaptive_sampler.compute_sampled() is True

        assert self.adaptive_sampler.compute_sampled() is False
        self.assertEqual(self.adaptive_sampler.sampled_count, max_sampled)

    def test_sampling_probability_not_sampled(self):
        self.adaptive_sampler.computed_count = 100
        self.adaptive_sampler.reset()

        self.value = 99
        self.patch()

        assert self.adaptive_sampler.compute_sampled() is False

    def test_sampling_probability_count_above_target(self):
        count = 2 * self.target

        self.adaptive_sampler.computed_count = count
        self.adaptive_sampler.reset()

        self.patch()
        self.value = count - 1

        assert self.adaptive_sampler.compute_sampled() is False

        self.value = self.target
        assert self.adaptive_sampler.compute_sampled() is False

    def test_sampling_probability_count_below_target(self):
        self.adaptive_sampler.reset()

        for _ in range(self.target):
            assert self.adaptive_sampler.compute_sampled() is True

        self.patch()
        self.value = self.target - 1

        assert self.adaptive_sampler.compute_sampled() is False

    def test_exponential_backoff(self):
        self.adaptive_sampler.computed_count = 100
        self.adaptive_sampler.reset()

        self.patch()
        self.value = self.target - 1

        # The first #[target] values should be sampled when randrange is
        # target-1
        for sample_num in range(self.target):
            assert self.adaptive_sampler.compute_sampled() is True

        # For the next #[target], we should be exponentially backed off
        for sample_num in range(self.target, 2 * self.target):
            ratio = float(self.target) / sample_num
            limit = (self.target ** ratio -
                     self.target ** 0.5)

            assert self.adaptive_sampler.adaptive_target == limit

            self.value = 0
            assert self.adaptive_sampler.compute_sampled() is True

        # Never sample past the maximum
        self.value = 0.0
        assert self.adaptive_sampler.compute_sampled() is False

    def test_target_zero(self):
        self.adaptive_sampler = AdaptiveSampler(0, 60.0)

        assert self.adaptive_sampler.compute_sampled() is False

        self.adaptive_sampler.computed_count = 0
        self.adaptive_sampler.reset()

        assert self.adaptive_sampler.compute_sampled() is False
