import pytest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace

from testing_support.fixtures import override_application_settings


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
))
def test_span_events(trace_type, args):

    @background_task('test_span_events')
    @override_application_settings({'feature_flag': set(['span_events'])})
    def _test():
        transaction = current_transaction()

        with trace_type(transaction, *args):
            pass

    _test()
