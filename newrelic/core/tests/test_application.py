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
        self.application.adaptive_sampler._lock.acquire()

    def tearDown(self):
        # Release the lock held by the tests
        try:
            self.application.adaptive_sampler._lock.release()
        except RuntimeError:
            pass

        super(TestApplicationLocking, self).tearDown()

    def test_compute_sampled_waits_for_lock(self):
        # Create a thread which calls compute_sampled
        thread = threading.Thread(name='compute_sampled',
                target=self.application.compute_sampled)
        thread.start()

        try:
            # Assert that the sampled count does not change yet (since the lock
            # is acquired)
            assert self.application.adaptive_sampler.sampled_count == 0
        finally:
            # Release the lock
            self.application.adaptive_sampler._lock.release()

        # Join thread
        thread.join(timeout=1.0)

        # Re-acquire the lock
        self.application.adaptive_sampler._lock.acquire()

        # Check that sampled count is now 1
        assert self.application.adaptive_sampler.sampled_count == 1


class TestUnactivatedApplication(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        super(TestUnactivatedApplication, self).setUp()
        self.application = newrelic.core.application.Application('foobar')

    def test_compute_sampled_returns_false(self):
        assert self.application.compute_sampled() is False
