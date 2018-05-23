import threading
import newrelic.tests.test_cases


class TestSamplingProbability(newrelic.tests.test_cases.TestCase):

    # set requires_collector to True so that TestCase will create an
    # application for us
    requires_collector = True

    def setUp(self):
        super(TestSamplingProbability, self).setUp()
        # Since these unit tests are modifying the application object, we must
        # prevent the harvest thread from clobbering our edits
        self.application._stats_lock.acquire()

        self.application._transaction_sampled_count = 0
        self.application._max_sampled = 10
        self.application._min_sampling_priority = 0.0

    def tearDown(self):
        # Release the lock held by the tests
        try:
            self.application._stats_lock.release()
        except RuntimeError:
            pass

        super(TestSamplingProbability, self).tearDown()

    def test_compute_sampled_waits_for_lock(self):
        # Create a thread which calls compute_sampled
        thread = threading.Thread(name='compute_sampled',
                target=self.application.compute_sampled, args=(1.0,))
        thread.start()

        try:
            # Assert that the sampled count does not change yet (since the lock
            # is acquired)
            assert self.application._transaction_sampled_count == 0
        finally:
            # Release the lock
            self.application._stats_lock.release()

        # Join thread
        thread.join(timeout=1.0)

        # Re-acquire the lock
        self.application._stats_lock.acquire()

        # Check that sampled count is now 1
        assert self.application._transaction_sampled_count == 1

    def test_sampling_probability_first_harvest(self):
        target = self.application.configuration.agent_limits.sampling_target
        self.application._max_sampled = target

        for _ in range(target):
            assert self.application.compute_sampled(0.0) is True

        assert self.application.compute_sampled(1.0) is False
        self.assertEqual(self.application._transaction_sampled_count, target)

    def test_sampling_probability_max_sampled(self):
        # Set max_sampled to 20
        target = 2 * self.application._sampling_target
        self.application._max_sampled = target

        for _ in range(20):
            assert self.application.compute_sampled(1.0) is True

        assert self.application.compute_sampled(1.0) is False
        self.assertEqual(self.application._transaction_sampled_count, 20)

    def test_sampling_probability_not_sampled(self):
        # Should not sample anything
        self.application._min_sampling_priority = 100.0

        assert self.application.compute_sampled(1.0) is False

    def test_sampling_probability_count_above_target(self):
        target = self.application.configuration.agent_limits.sampling_target
        count = 2 * target

        expected_min_sampling_priority = (1.0 - float(target) / count)

        self.application._transaction_count = count
        self.application.harvest()
        self.assertAlmostEqual(self.application._min_sampling_priority,
                expected_min_sampling_priority)

    def test_sampling_probability_count_below_target(self):
        self.application._transaction_count = 1
        self.application.harvest()

        self.assertEqual(self.application._min_sampling_priority, 0.0)

    def test_max_sampled_reset_on_harvest(self):
        self.application._transaction_count = 0
        self.application.harvest()

        target = (2 * self.application.
                configuration.agent_limits.sampling_target)
        self.assertEqual(self.application._max_sampled, target)

    def test_sampling_ratio_not_recomputed_if_transaction_count_0(self):
        self.application._transaction_count = 50
        self.application.harvest()

        priority = self.application._min_sampling_priority

        self.assertEqual(self.application._transaction_count, 0)
        self.application.harvest()

        self.assertEqual(self.application._min_sampling_priority, priority)

    def test_count_reset_after_harvest(self):
        self.application._transaction_sampled_count = 10
        self.application._transaction_count = 100

        self.application.harvest()

        self.assertEqual(self.application._transaction_sampled_count, 0)
        self.assertEqual(self.application._transaction_count, 0)

    def test_exponential_backoff(self):
        self.application._transaction_count = 100

        expectedMSP = [
            0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
            0.9512462826139941, 0.9642301587871667, 0.9735792049702137,
            0.9805646189006507, 0.9859434773568351, 0.9901897153501046,
            0.9936126144884015, 0.9964212290549166, 0.998761182830125
        ]

        for tsc in range(0, 20):
            self.application._transaction_sampled_count = tsc
            self.application._calc_min_sampling_priority()

            diff = self.application._min_sampling_priority - expectedMSP[tsc]
            self.assertEqual(diff < 0.001, True)
