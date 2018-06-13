import sys
from newrelic.api.background_task import BackgroundTask
from newrelic.core.config import finalize_application_settings


class MockApplication(object):
    def __init__(self, name='Python Application'):
        self.global_settings = finalize_application_settings()
        self.global_settings.enabled = True
        self.settings = finalize_application_settings({})
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        return None

    def compute_sampled(self, priority):
        return True


class TimeSuite:

    def setup(self):
        app = MockApplication()
        self.txn = BackgroundTask(app, 'foo')
        self.txn.__enter__()
        try:
            raise ValueError("oops!")
        except ValueError:
            self.exc_info = sys.exc_info()

    def time_exit_no_error(self):
        self.txn.__exit__(None, None, None)

    def time_exit_with_error(self):
        self.txn.__exit__(*self.exc_info)
