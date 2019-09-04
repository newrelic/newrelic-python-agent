import threading
import newrelic.tests.test_cases
import newrelic.core.application as application


class TestAgentLocking(newrelic.tests.test_cases.TestCase):
    def setUp(self):
        super(TestAgentLocking, self).setUp()
        self.original_activate_session = \
                application.Application.activate_session
        self.application_active = event = threading.Event()

        def event_wait(self_class, activate_agent, timeout):
            event.wait(timeout)

        application.Application.activate_session = event_wait

    def tearDown(self):
        super(TestAgentLocking, self).tearDown()
        self.application_active.set()
        application.Application.activate_session = \
                self.original_activate_session

    def test_activate_application_holds_lock_until_application_active(self):
        thread_a = threading.Thread(name='activate_session',
                target=self.agent.activate_application,
                args=(None,), kwargs={'timeout': 10000})
        thread_a.start()

        thread_b = threading.Thread(name='wait_for_activate',
                target=self.agent.activate_application,
                args=(None,), kwargs={'timeout': 10000})
        thread_b.start()

        # Both threads should wait for the application to activate
        thread_a.join(timeout=0.1)
        assert thread_a.is_alive() is True

        thread_b.join(timeout=0.1)
        assert thread_b.is_alive() is True

        # Complete application activation
        self.application_active.set()

        # Both activation threads should now exit
        thread_a.join(timeout=0.1)
        thread_b.join(timeout=0.1)

        assert thread_a.is_alive() is False
        assert thread_b.is_alive() is False
