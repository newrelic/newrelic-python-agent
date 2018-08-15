import sys

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import Transaction

from benchmarks.util import MockApplication

_function_trace_kwargs = {
        'name': 'benchmark-function-trace',
}


class TimeTraceInit(object):

    def setup(self):
        app = MockApplication()
        self.transaction = Transaction(app)
        self.transaction.__enter__()

    def teardown(self):
        self.transaction.__exit__(None, None, None)

    def time_time_trace_init(self):
        TimeTrace(self.transaction)

    def time_function_trace_init(self):
        FunctionTrace(self.transaction, **_function_trace_kwargs)


class TimeTraceEnter(object):

    def setup(self):
        app = MockApplication()
        self.transaction = Transaction(app)
        self.transaction.__enter__()
        self.time_trace = TimeTrace(self.transaction)

    def teardown(self):
        self.transaction.__exit__(None, None, None)

    def time_time_trace_enter(self):
        self.time_trace.__enter__()


class TimeTraceExit(object):

    def setup(self):
        app = MockApplication()
        self.transaction = Transaction(app)
        self.transaction.__enter__()
        self.time_trace = TimeTrace(self.transaction)
        self.function_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)
        self.time_trace.__enter__()
        self.function_trace.__enter__()

        try:
            raise ValueError('oops!')
        except ValueError:
            self.exc_info = sys.exc_info()

    def teardown(self):
        self.transaction.__exit__(None, None, None)
        self.exc_info = None

    def time_time_trace_exit_no_error(self):
        self.time_trace.__exit__(None, None, None)

    def time_time_trace_exit_with_error(self):
        self.time_trace.__exit__(*self.exc_info)

    def time_function_trace_exit_no_error(self):
        self.function_trace.__exit__(None, None, None)

    def time_function_trace_exit_with_error(self):
        self.function_trace.__exit__(*self.exc_info)
