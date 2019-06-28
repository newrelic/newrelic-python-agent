import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import current_trace
from newrelic.api.background_task import background_task

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace, function_trace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace

from testing_support.fixtures import (override_application_settings,
        function_not_called)
from testing_support.validators.validate_span_events import (
        validate_span_events)


@pytest.mark.parametrize('dt_enabled', (True, False))
@pytest.mark.parametrize('span_events_enabled', (True, False))
@pytest.mark.parametrize('txn_sampled', (True, False))
def test_span_events(dt_enabled, span_events_enabled, txn_sampled):
    guid = 'dbb536c53b749e0b'
    sentinel_guid = '0687e0c371ea2c4e'
    function_guid = '482439c52de807ee'
    priority = 0.5

    @function_trace(name='child')
    def child():
        pass

    @function_trace(name='function')
    def function():
        current_trace().guid = function_guid
        child()

    _settings = {
        'distributed_tracing.enabled': dt_enabled,
        'span_events.enabled': span_events_enabled
    }

    count = 0
    if dt_enabled and span_events_enabled and txn_sampled:
        count = 1

    exact_intrinsics_common = {
        'type': 'Span',
        'transactionId': guid,
        'sampled': txn_sampled,
        'priority': priority,
        'category': 'generic',
    }
    expected_intrinsics = ('timestamp', 'duration')

    exact_intrinsics_root = exact_intrinsics_common.copy()
    exact_intrinsics_root['name'] = 'Function/transaction'
    exact_intrinsics_root['nr.entryPoint'] = True

    exact_intrinsics_function = exact_intrinsics_common.copy()
    exact_intrinsics_function['name'] = 'Function/function'
    exact_intrinsics_function['parentId'] = sentinel_guid

    exact_intrinsics_child = exact_intrinsics_common.copy()
    exact_intrinsics_child['name'] = 'Function/child'
    exact_intrinsics_child['parentId'] = function_guid

    @validate_span_events(count=count,
            expected_intrinsics=['nr.entryPoint'])
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_root,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_function,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_child,
            expected_intrinsics=expected_intrinsics)
    @override_application_settings(_settings)
    @background_task(name='transaction')
    def _test():
        # Force intrinsics
        txn = current_transaction()
        current_trace().guid = sentinel_guid
        txn.guid = guid
        txn._priority = priority
        txn._sampled = txn_sampled

        function()

    _test()


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
))
def test_each_span_type(trace_type, args):
    @validate_span_events(count=2)
    @override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })
    @background_task(name='test_each_span_type')
    def _test():

        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(transaction, *args):
            pass

    _test()


@pytest.mark.parametrize('sql,sql_format,expected', (
    pytest.param(
            'a' * 2001,
            'raw',
            ''.join(['a'] * 1997 + ['...']),
            id='truncate'),
    pytest.param(
            'a' * 2000,
            'raw',
            ''.join(['a'] * 2000),
            id='no_truncate'),
    pytest.param(
            'select * from %s' % ''.join(['?'] * 2000),
            'obfuscated',
            'select * from %s...' % (
                    ''.join(['?'] * (2000 - len('select * from ') - 3))),
            id='truncate_obfuscated'),
    pytest.param('select 1', 'off', ''),
    pytest.param('select 1', 'raw', 'select 1'),
    pytest.param('select 1', 'obfuscated', 'select ?'),
))
def test_database_db_statement_format(sql, sql_format, expected):
    @validate_span_events(count=1, exact_agents={
        'db.statement': expected,
    })
    @override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'transaction_tracer.record_sql': sql_format,
    })
    @background_task(name='test_database_db_statement_format')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with DatabaseTrace(transaction, sql):
            pass

    _test()


@validate_span_events(
    count=1,
    exact_intrinsics={'category': 'datastore'},
    unexpected_agents=['db.statement'],
)
@override_application_settings({
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
    'span_events.attributes.exclude': ['db.statement'],
})
@background_task(name='test_database_db_statement_exclude')
def test_database_db_statement_exclude():
    transaction = current_transaction()
    transaction._sampled = True

    with DatabaseTrace(transaction, 'select 1'):
        pass


@pytest.mark.parametrize('exclude_url', (True, False))
def test_external_spans(exclude_url):
    override_settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    if exclude_url:
        override_settings['span_events.attributes.exclude'] = ['http.url']
        exact_agents = {}
        unexpected_agents = ['http.url']
    else:
        exact_agents = {'http.url': 'http://example.com/foo'}
        unexpected_agents = []

    @validate_span_events(
        count=1,
        exact_intrinsics={
            'name': 'External/example.com/library/get',
            'type': 'Span',
            'sampled': True,

            'category': 'http',
            'span.kind': 'client',
            'component': 'library',
            'http.method': 'get',
        },
        exact_agents=exact_agents,
        unexpected_agents=unexpected_agents,
        expected_intrinsics=('priority',),
    )
    @override_application_settings(override_settings)
    @background_task(name='test_external_spans')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with ExternalTrace(
                transaction,
                library='library',
                url='http://example.com/foo?secret=123',
                method='get'):
            pass

    _test()


@pytest.mark.parametrize('kwarg_override,attr_override', (
    ({'url': 'a' * 256}, {'http.url': 'a' * 255}),
    ({'library': 'a' * 256}, {'component': 'a' * 255}),
    ({'method': 'a' * 256}, {'http.method': 'a' * 255}),
))
@override_application_settings({
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
})
def test_external_span_limits(kwarg_override, attr_override):

    exact_intrinsics = {
        'type': 'Span',
        'sampled': True,

        'category': 'http',
        'span.kind': 'client',
        'component': 'library',
        'http.method': 'get',
    }
    exact_agents = {
        'http.url': 'http://example.com/foo',
    }
    for attr_name, attr_value in attr_override.items():
        if attr_name in exact_agents:
            exact_agents[attr_name] = attr_value
        else:
            exact_intrinsics[attr_name] = attr_value

    kwargs = {
        'library': 'library',
        'url': 'http://example.com/foo?secret=123',
        'method': 'get',
    }
    kwargs.update(kwarg_override)

    @validate_span_events(
        count=1,
        exact_intrinsics=exact_intrinsics,
        exact_agents=exact_agents,
        expected_intrinsics=('priority',),
    )
    @background_task(name='test_external_spans')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with ExternalTrace(
                transaction,
                **kwargs):
            pass

    _test()


@pytest.mark.parametrize('kwarg_override,attribute_override', (
    ({'host': 'a' * 256},
     {'peer.hostname': 'a' * 255, 'peer.address': 'a' * 255}),
    ({'port_path_or_id': 'a' * 256, 'host': 'a'},
     {'peer.hostname': 'a', 'peer.address': 'a:' + 'a' * 253}),
    ({'database_name': 'a' * 256}, {'db.instance': 'a' * 255}),
))
@override_application_settings({
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
})
def test_datastore_span_limits(kwarg_override, attribute_override):

    exact_intrinsics = {
        'type': 'Span',
        'sampled': True,

        'category': 'datastore',
        'span.kind': 'client',
        'component': 'library',
        'peer.hostname': 'foo',
        'peer.address': 'foo:1234',
    }

    db_instance_override = attribute_override.pop('db.instance', None)
    if db_instance_override:
        exact_agents = {
            'db.instance': db_instance_override
        }
    else:
        exact_agents = {
            'db.instance': 'db',
        }

    exact_intrinsics.update(attribute_override)

    kwargs = {
        'product': 'library',
        'target': 'table',
        'operation': 'operation',
        'host': 'foo',
        'port_path_or_id': 1234,
        'database_name': 'db',
    }
    kwargs.update(kwarg_override)

    @validate_span_events(
        count=1,
        exact_intrinsics=exact_intrinsics,
        expected_intrinsics=('priority',),
        exact_agents=exact_agents,
    )
    @background_task(name='test_external_spans')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with DatastoreTrace(
                transaction,
                **kwargs):
            pass

    _test()


@pytest.mark.parametrize('collect_span_events', (False, True))
@pytest.mark.parametrize('span_events_enabled', (False, True))
def test_collect_span_events_override(collect_span_events,
        span_events_enabled):

    if collect_span_events and span_events_enabled:
        spans_expected = True
    else:
        spans_expected = False

    span_count = 2 if spans_expected else 0

    @validate_span_events(count=span_count)
    @override_application_settings({
        'transaction_tracer.enabled': False,
        'distributed_tracing.enabled': True,
        'span_events.enabled': span_events_enabled,
        'collect_span_events': collect_span_events
    })
    @background_task(name='test_collect_span_events_override')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with FunctionTrace(transaction, 'span_generator'):
            pass

    if not spans_expected:
        _test = function_not_called(
                'newrelic.core.attribute',
                'resolve_agent_attributes')(_test)

    _test()


@pytest.mark.parametrize('include_attribues', (True, False))
def test_span_event_agent_attributes(include_attribues):
    override_settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }
    if include_attribues:
        count = 1
        override_settings['attributes.include'] = ['*']
    else:
        count = 0

    @override_application_settings(override_settings)
    @validate_span_events(
            count=0, expected_agents=['webfrontend.queue.seconds'])
    @validate_span_events(
            count=count,
            exact_agents={'trace1_a': 'foobar', 'trace1_b': 'barbaz'},
            unexpected_agents=['trace2_a', 'trace2_b'])
    @validate_span_events(
            count=count,
            exact_agents={'trace2_a': 'foobar', 'trace2_b': 'barbaz'},
            unexpected_agents=['trace1_a', 'trace1_b'])
    @background_task(name='test_span_event_agent_attributes')
    def _test():
        transaction = current_transaction()
        transaction.queue_start = 1.0
        transaction._sampled = True

        with FunctionTrace(transaction, 'trace1') as trace_1:
            trace_1._add_agent_attribute('trace1_a', 'foobar')
            trace_1._add_agent_attribute('trace1_b', 'barbaz')
            with FunctionTrace(transaction, 'trace2') as trace_2:
                trace_2._add_agent_attribute('trace2_a', 'foobar')
                trace_2._add_agent_attribute('trace2_b', 'barbaz')

    _test()
