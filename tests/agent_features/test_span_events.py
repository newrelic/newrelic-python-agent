# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import sys

from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import (current_trace,
        add_custom_span_attribute, notice_error)
from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace, function_trace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace

from testing_support.fixtures import (override_application_settings,
        function_not_called, validate_tt_segment_params,
        validate_transaction_metrics, dt_enabled,
        validate_transaction_event_attributes)
from testing_support.validators.validate_span_events import (
        validate_span_events)

ERROR = ValueError("whoops")
ERROR_NAME = callable_name(ERROR)


@pytest.mark.parametrize('dt_enabled', (True, False))
@pytest.mark.parametrize('span_events_enabled', (True, False))
@pytest.mark.parametrize('txn_sampled', (True, False))
def test_span_events(dt_enabled, span_events_enabled, txn_sampled):
    guid = 'dbb536c53b749e0b'
    sentinel_guid = '0687e0c371ea2c4e'
    function_guid = '482439c52de807ee'
    transaction_name = 'OtherTransaction/Function/transaction'
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
    exact_intrinsics_root['transaction.name'] = transaction_name
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

        with trace_type(*args):
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

        with DatabaseTrace(sql):
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

    with DatabaseTrace('select 1'):
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

        with ExternalTrace(**kwargs):
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
    }

    exact_agents = {
        'db.instance': 'db',
        'peer.hostname': 'foo',
        'peer.address': 'foo:1234',
    }

    for k, v in attribute_override.items():
        if k in exact_agents:
            exact_agents[k] = v
        else:
            exact_intrinsics[k] = v

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

        with DatastoreTrace(**kwargs):
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

        with FunctionTrace('span_generator'):
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
            count=count, expected_agents=['webfrontend.queue.seconds'])
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

        with FunctionTrace('trace1') as trace_1:
            trace_1._add_agent_attribute('trace1_a', 'foobar')
            trace_1._add_agent_attribute('trace1_b', 'barbaz')
            with FunctionTrace('trace2') as trace_2:
                trace_2._add_agent_attribute('trace2_a', 'foobar')
                trace_2._add_agent_attribute('trace2_b', 'barbaz')

    _test()


class FakeTrace(object):
    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
    (FakeTrace, ()),
))
@pytest.mark.parametrize('exclude_attributes', (True, False))
def test_span_event_user_attributes(trace_type, args, exclude_attributes):

    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    forgone_params = ['invalid_value', ]
    expected_params = {'trace1_a': 'foobar', 'trace1_b': 'barbaz'}
    # We expect user_attributes to be included by default
    if exclude_attributes:
        count = 0
        _settings['attributes.exclude'] = ['*']
        forgone_params.extend(('trace1_a', 'trace1_b'))
        expected_trace_params = {}
    else:
        expected_trace_params = expected_params
        count = 1

    @override_application_settings(_settings)
    @validate_span_events(
        count=count,
        exact_users=expected_params,
        unexpected_users=forgone_params,)
    @validate_tt_segment_params(exact_params=expected_trace_params,
        forgone_params=forgone_params)
    @background_task(name='test_span_event_user_attributes')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(*args):
            add_custom_span_attribute('trace1_a', 'foobar')
            add_custom_span_attribute('trace1_b', 'barbaz')
            add_custom_span_attribute('invalid_value', sys.maxsize + 1)

    _test()


@validate_span_events(count=1, exact_users={'foo': 'b'})
@dt_enabled
@background_task(name='test_span_user_attribute_overrides_transaction_attribute')
def test_span_user_attribute_overrides_transaction_attribute():
    transaction = current_transaction()

    transaction.add_custom_parameter('foo', 'a')
    add_custom_span_attribute('foo', 'b')
    transaction.add_custom_parameter('foo', 'c')


@override_application_settings({'attributes.include': '*'})
@validate_span_events(count=1, exact_agents={'foo': 'b'})
@dt_enabled
@background_task(name='test_span_agent_attribute_overrides_transaction_attribute')
def test_span_agent_attribute_overrides_transaction_attribute():
    transaction = current_transaction()
    trace = current_trace()

    transaction._add_agent_attribute('foo', 'a')
    trace._add_agent_attribute('foo', 'b')
    transaction._add_agent_attribute('foo', 'c')


def test_span_custom_attribute_limit():
    """
    This test validates that span attributes take precedence when
    adding the span and transaction custom parameters that reach the
    maximum user attribute limit.
    """
    span_custom_attrs = []
    txn_custom_attrs = []
    unexpected_txn_attrs = []

    for i in range(128):
        if i < 64:
            span_custom_attrs.append('span_attr%i' % i)
        txn_custom_attrs.append('txn_attr%i' % i)

    unexpected_txn_attrs.extend(span_custom_attrs)
    span_custom_attrs.extend(txn_custom_attrs[:64])
    expected_txn_attrs = {'user': txn_custom_attrs, 'agent': [],
                                   'intrinsic': []}
    expected_absent_txn_attrs = {'agent': [],
                                  'user':  unexpected_txn_attrs,
                                  'intrinsic': []}

    @override_application_settings({'attributes.include': '*'})
    @validate_transaction_event_attributes(expected_txn_attrs,
                                           expected_absent_txn_attrs)
    @validate_span_events(count=1,
                          expected_users=span_custom_attrs,
                          unexpected_users=txn_custom_attrs[64:])
    @dt_enabled
    @background_task(name='test_span_attribute_limit')
    def _test():
        transaction = current_transaction()

        for i in range(128):
            transaction.add_custom_parameter('txn_attr%i' % i, 'txnValue')
            if i < 64:
                add_custom_span_attribute('span_attr%i' % i, 'spanValue')
    _test()


_span_event_metrics = [("Supportability/SpanEvent/Errors/Dropped", None)]


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
    (FakeTrace, ()),
))
def test_span_event_error_attributes_notice_error(trace_type, args):

    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    error = ValueError("whoops")

    exact_agents = {
        'error.class': callable_name(error),
        'error.message': 'whoops',
    }

    @override_application_settings(_settings)
    @validate_transaction_metrics(
            'test_span_event_error_attributes_notice_error',
            background_task=True,
            rollup_metrics=_span_event_metrics)
    @validate_span_events(
        count=1,
        exact_agents=exact_agents,)
    @background_task(name='test_span_event_error_attributes_notice_error')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(*args):
            try:
                raise ValueError("whoops")
            except:
                notice_error()

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
def test_span_event_error_attributes_observed(trace_type, args):

    error = ValueError("whoops")

    exact_agents = {
        'error.class': callable_name(error),
        'error.message': 'whoops',
    }

    # Verify errors are not recorded since notice_error is not called
    rollups = [('Errors/all', None)] + _span_event_metrics

    @dt_enabled
    @validate_transaction_metrics(
            'test_span_event_error_attributes_observed',
            background_task=True,
            rollup_metrics=rollups)
    @validate_span_events(
        count=1,
        exact_agents=exact_agents,)
    @background_task(name='test_span_event_error_attributes_observed')
    def _test():
        try:
            with trace_type(*args):
                raise error
        except:
            pass

    _test()


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
    (FakeTrace, ()),
))
@dt_enabled
@validate_span_events(count=1,
        exact_agents={'error.class': ERROR_NAME, 'error.message': 'whoops'})
@background_task(name='test_span_event_notice_error_overrides_observed')
def test_span_event_notice_error_overrides_observed(trace_type, args):
    try:
        with trace_type(*args):
            try:
                raise ERROR
            except:
                notice_error()
                raise ValueError
    except ValueError:
        pass


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
    (FakeTrace, ()),
))
@override_application_settings({'error_collector.enabled': False})
@validate_span_events(count=0, expected_agents=['error.class'])
@validate_span_events(count=0, expected_agents=['error.message'])
@dt_enabled
@background_task(name='test_span_event_errors_disabled')
def test_span_event_errors_disabled(trace_type, args):
    with trace_type(*args):
        try:
            raise ValueError("whoops")
        except:
            notice_error()


_metrics = [("Supportability/SpanEvent/Errors/Dropped", 2)]


@pytest.mark.parametrize('trace_type,args', (
    (FunctionTrace, ('name', )),
    (FakeTrace, ()),
))
def test_span_event_multiple_errors(trace_type, args):
    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    error = ValueError("whoops")

    exact_agents = {
        'error.class': callable_name(error),
        'error.message': 'whoops',
        "error.expected": False,
    }

    @override_application_settings(_settings)
    @validate_span_events(
        count=1,
        exact_agents=exact_agents,)
    @validate_transaction_metrics("test_span_event_multiple_errors",
            background_task=True,
            rollup_metrics=_metrics)
    @background_task(name='test_span_event_multiple_errors')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(*args):
            try:
                raise RuntimeError("whoaa")
            except:
                notice_error()
            try:
                raise RuntimeError("whoo")
            except:
                notice_error()
            try:
                raise ValueError("whoops")
            except:
                notice_error()

    _test()
