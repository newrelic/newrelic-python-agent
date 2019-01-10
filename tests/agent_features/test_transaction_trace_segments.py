import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import external_trace, ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace

from testing_support.fixtures import (override_application_settings,
        validate_tt_segment_params)


@external_trace('lib', 'https://example.com/path?q=q#frag')
def external():
    pass


@validate_tt_segment_params(present_params=('http.url',))
@background_task(name='test_external_segment_attributes_default')
def test_external_segment_attributes_default():
    external()


@override_application_settings({
    'transaction_segments.attributes.exclude': ['http.url'],
})
@validate_tt_segment_params(forgone_params=('http.url',))
@background_task(name='test_external_segment_attributes_disabled')
def test_external_segment_attributes_disabled():
    external()


@validate_tt_segment_params(exact_params={'http.url': 'http://example.org'})
@background_task(name='test_external_user_params_override_url')
def test_external_user_params_override_url():
    transaction = current_transaction()
    with ExternalTrace(transaction, 'lib', 'http://example.com') as t:
        # Pretend like this is a user attribute and it's legal to do this
        t.params['http.url'] = 'http://example.org'


@validate_tt_segment_params(exact_params={'db.instance': 'a' * 255})
@background_task(name='test_datastore_db_instance_truncation')
def test_datastore_db_instance_truncation():
    transaction = current_transaction()
    with DatastoreTrace(transaction, 'db_product', 'db_target', 'db_operation',
            database_name='a' * 256):
        pass


@validate_tt_segment_params(exact_params={'db.instance': 'a' * 255})
@background_task(name='test_database_db_instance_truncation')
def test_database_db_instance_truncation():
    transaction = current_transaction()
    with DatabaseTrace(transaction, 'select * from foo',
            database_name='a' * 256):
        pass


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
))
def test_each_segment_type(trace_type, args):
    @validate_tt_segment_params(exact_params={'blah': 'bloo'})
    @override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'attributes.include': ['blah'],
    })
    @background_task(name='test_each_segment_type')
    def _test():

        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(transaction, *args) as trace:
            trace._add_agent_attribute('blah', 'bloo')

    _test()
