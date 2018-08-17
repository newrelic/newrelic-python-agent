import weakref
import sys

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import Transaction

from benchmarks.util import MockApplication, MockTransaction


class _database_trace_module(object):
    _nr_database_product = 'db-product'
    _nr_quoting_style = 'single'
    _nr_explain_query = 'explain'
    _nr_explain_stmts = ('select', 'drop', 'insert', 'cookies')
    _nr_datastore_instance_feature_flag = True

    @staticmethod
    def _nr_instance_info(*args, **kwargs):
        return 'host', 'port_path_or_id', 'database_name'


_function_trace_kwargs = {
        'name': 'benchmark-function-trace',
}
_external_trace_kwargs = {
        'library': 'external-trace-library',
        'url': 'external-trace-url',
        'method': 'GET',
}
_database_trace_kwargs = {
        'sql': 'SELECT * FROM foo',
        'dbapi2_module': _database_trace_module,
        'connect_params': ((), {}),
        'cursor_params': ((), {}),
        'sql_parameters': ((), {}),
        'execute_params': ((), {}),
        'host': 'localhost',
        'port_path_or_id': 1234,
        'database_name': 'mydb',
}
_datastore_trace_kwargs = {
        'product': 'my-product',
        'target': 'my-target',
        'operation': 'my-operation',
        'host': 'localhost',
        'port_path_or_id': 1234,
        'database_name': 'mydb',
}
_memcache_trace_kwargs = {
        'command': 'do foo and bar please',
}
_message_trace_kwargs = {
        'library': 'mylibraryissocool',
        'operation': 'include',
        'destination_type': 'Queue',
        'destination_name': 'queuetee',
        'params': {'param1': 1, 'param2': 2},
}
_solr_trace_kwargs = {
        'library': 'Solr Storm',
        'command': 'commanding',
}
_settings = {
        'transaction_tracer.stack_trace_threshold': 0.0,
        'transaction_tracer.explain_threshold': 0.0,
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

    def time_database_trace_init(self):
        self.transaction._string_cache = {}
        DatabaseTrace(self.transaction, **_database_trace_kwargs)

    def time_datastore_trace_init(self):
        self.transaction._string_cache = {}
        DatastoreTrace(self.transaction, **_datastore_trace_kwargs)

    def time_memcache_trace_init(self):
        MemcacheTrace(self.transaction, **_memcache_trace_kwargs)

    def time_message_trace_init(self):
        self.transaction._string_cache = {}
        MessageTrace(self.transaction, **_message_trace_kwargs)

    def time_solr_trace_init(self):
        SolrTrace(self.transaction, **_solr_trace_kwargs)


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


class TimeTraceProcessChild(object):

    def setup(self):
        app = MockApplication()
        self.transaction = MockTransaction(app)
        self.transaction.activated = True
        self._transaction = weakref.ref(self.transaction)

        self.async_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)
        self.async_trace.activated = True
        self.async_trace.is_async = True
        self.async_trace.child_count = 1
        self.async_node = self.async_trace.create_node()

        self.sync_trace = FunctionTrace(self.transaction,
                **_function_trace_kwargs)
        self.sync_trace.activated = True
        self.sync_trace.is_async = False
        self.sync_trace.child_count = 1
        self.sync_node = self.sync_trace.create_node()

    def time_async_process_child(self):
        self.async_trace.children = []
        self.async_trace.process_child(self.async_node)

    def time_sync_process_child(self):
        self.sync_trace.children = []
        self.sync_trace.process_child(self.sync_node)


class TimeTraceFinalizeData(object):

    def setup(self):
        app = MockApplication(settings=_settings)
        self.transaction = MockTransaction(app)
        self.database_trace = DatabaseTrace(self.transaction,
                **_database_trace_kwargs)

    def time_database_trace_finalize_data(self):
        self.transaction._string_cache = {}
        self.database_trace.finalize_data(self.transaction)
