import sys

from newrelic.api.function_trace import FunctionTrace
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

    def time_function_trace_init(self):
        FunctionTrace(self.transaction, **_function_trace_kwargs)


class TimeTraceEnter(object):

    def setup(self):
        app = MockApplication()
        self.transaction = Transaction(app)
        self.transaction.__enter__()
        self.function_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)

    def teardown(self):
        self.transaction.__exit__(None, None, None)

    def time_function_trace_enter(self):
        self.function_trace.__enter__()


class TimeTraceExit(object):

    def setup(self):
        app = MockApplication()
        self.transaction = Transaction(app)
        self.transaction.__enter__()
        self.function_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)
        self.function_trace.__enter__()

        try:
            raise ValueError('oops!')
        except ValueError:
            self.exc_info = sys.exc_info()

    def teardown(self):
        self.transaction.__exit__(None, None, None)
        self.exc_info = None

    def time_function_trace_exit_no_error(self):
        self.function_trace.__exit__(None, None, None)

    def time_function_trace_exit_with_error(self):
        self.function_trace.__exit__(*self.exc_info)
