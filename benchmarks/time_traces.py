import weakref
import sys

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import Transaction

from benchmarks.util import MockApplication, MockTransaction

_function_trace_kwargs = {
        'name': 'benchmark-function-trace',
}
_external_trace_kwargs = {
        'library': 'external-trace-library',
        'url': 'external-trace-url',
        'method': 'GET',
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

    def time_external_trace_init(self):
        ExternalTrace(self.transaction, **_external_trace_kwargs)


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
        self.transaction = MockTransaction(app)
        self.transaction.activated = True
        self._transaction = weakref.ref(self.transaction)

        self.function_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)

        self.function_trace.activated = True

        try:
            raise ValueError('oops!')
        except ValueError:
            self.exc_info = sys.exc_info()

    def teardown(self):
        self.exc_info = None

    def time_function_trace_exit_no_error(self):
        self.function_trace.parent = self.transaction.current_node
        self.function_trace._transaction = self._transaction
        self.function_trace.__exit__(None, None, None)

    def time_function_trace_exit_with_error(self):
        self.function_trace.parent = self.transaction.current_node
        self.function_trace._transaction = self._transaction
        self.function_trace.__exit__(*self.exc_info)
