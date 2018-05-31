import threading
import newrelic.tests.test_cases


class TestApplicationLocking(newrelic.tests.test_cases.TestCase):

    # set requires_collector to True so that TestCase will create an
    # application for us
    requires_collector = True

    def setUp(self):
        super(TestApplicationLocking, self).setUp()
        # Since these unit tests are modifying the application object, we must
        # prevent the harvest thread from clobbering our edits
        self.application._stats_lock.acquire()

    def tearDown(self):
        # Release the lock held by the tests
        try:
            self.application._stats_lock.release()
        except RuntimeError:
            pass

        super(TestApplicationLocking, self).tearDown()

    def test_compute_sampled_waits_for_lock(self):
        # Create a thread which calls compute_sampled
        thread = threading.Thread(name='compute_sampled',
                target=self.application.compute_sampled, args=(1.0,))
        thread.start()

        try:
            # Assert that the sampled count does not change yet (since the lock
            # is acquired)
            assert self.application.adaptive_sampling.sampled_count == 0
        finally:
            # Release the lock
            self.application._stats_lock.release()

        # Join thread
        thread.join(timeout=1.0)

        # Re-acquire the lock
        self.application._stats_lock.acquire()

        # Check that sampled count is now 1
        assert self.application.adaptive_sampling.sampled_count == 1
