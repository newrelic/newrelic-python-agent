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
    with ExternalTrace('lib', 'http://example.com') as t:
        # Pretend like this is a user attribute and it's legal to do this
        t.params['http.url'] = 'http://example.org'


@validate_tt_segment_params(exact_params={'db.instance': 'a' * 255})
@background_task(name='test_datastore_db_instance_truncation')
def test_datastore_db_instance_truncation():
    with DatastoreTrace('db_product', 'db_target', 'db_operation',
            database_name='a' * 256):
        pass


@validate_tt_segment_params(exact_params={'db.instance': 'a' * 255})
@background_task(name='test_database_db_instance_truncation')
def test_database_db_instance_truncation():
    with DatabaseTrace('select * from foo',
            database_name='a' * 256):
        pass


@override_application_settings({
    'transaction_tracer.record_sql': 'raw',
})
@validate_tt_segment_params(exact_params={'db.statement': 'select 1'})
@background_task(name='test_database_db_statement')
def test_database_db_statement_default_enabled():
    with DatabaseTrace('select 1'):
        pass


@override_application_settings({
    'transaction_tracer.record_sql': 'raw',
    'agent_limits.sql_query_length_maximum': 1,
})
@validate_tt_segment_params(exact_params={'db.statement': 'a'})
@background_task(name='test_database_db_statement_truncation')
def test_database_db_statement_truncation():
    with DatabaseTrace('a' * 2):
        pass


@override_application_settings({
    'transaction_segments.attributes.exclude': ['db.*'],
})
@validate_tt_segment_params(forgone_params=('db.instance', 'db.statement'))
@background_task(name='test_database_segment_attributes_disabled')
def test_database_segment_attributes_disabled():
    transaction = current_transaction()
    with DatabaseTrace('select 1', database_name='foo'):
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

        with trace_type(*args) as trace:
            trace._add_agent_attribute('blah', 'bloo')

    _test()


@override_application_settings({
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
    'attributes.include': ['*'],
})
@background_task(name='test_attribute_overrides')
def test_attribute_overrides():
    with FunctionTrace('test_attribute_overrides_trace') as trace:
        trace.exclusive = 0.1
        trace._add_agent_attribute('exclusive_duration_millis', 0.2)
        trace._add_agent_attribute('test_attr', 'a')
        trace.add_custom_attribute('exclusive_duration_millis', 0.3)
        trace.add_custom_attribute('test_attr', 'b')
        node = trace.create_node()

    params = node.get_trace_segment_params(current_transaction().settings)

    assert params['exclusive_duration_millis'] == 100
    assert params['test_attr'] == 'b'
