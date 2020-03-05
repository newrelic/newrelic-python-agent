import pytest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import web_transaction
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace

from testing_support.validators.validate_span_events import (
        validate_span_events)
from testing_support.fixtures import (override_application_settings)


@pytest.mark.parametrize('wrapper_type,args', (
    (database_trace, ('select * from foo', )),
    (datastore_trace, ('db_product', 'db_target', 'db_operation')),
    (external_trace, ('lib', 'url')),
    (function_trace, ('name')),
    (memcache_trace, ('command', )),
    (message_trace, ('lib', 'operation', 'dst_type', 'dst_name')),
))
@pytest.mark.parametrize('test_default', (True, False))
def test_span_event_default_attributes(wrapper_type, args, test_default):
    override_settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    @override_application_settings(override_settings)
    @background_task(name='test_span_event_agent_attributes')
    @wrapper_type(*args)
    def _test():
        transaction = current_transaction()
        transaction.queue_start = 1.0
        transaction._sampled = True

    if test_default:
        count = 2
        expected = {}
        unexpected = ['file.name', 'line.number']
    else:
        count = 2
        override_settings['attributes.include'] = ['file.name', 'line.number']
        filename = _test.__code__.co_filename
        linenum = _test.__code__.co_firstlineno
        expected = {'file.name': filename, 'line.number': linenum}
        unexpected = []

    _test = validate_span_events(
        count=count,
        exact_agents=expected,
        unexpected_agents=unexpected)(_test)

    _test()


@pytest.mark.parametrize('test_default', (True, False))
def test_span_event_background_task_default_attributes(test_default):
    override_settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    @override_application_settings(override_settings)
    @background_task(name="test_span_event_background_task_default_attributes")
    def _test():
        transaction = current_transaction()
        transaction.queue_start = 1.0
        transaction._sampled = True

    if test_default:
        count = 1
        expected = {}
        unexpected = ['file.name', 'line.number']
    else:
        count = 1
        override_settings['attributes.include'] = ['file.name', 'line.number']
        filename = _test.__code__.co_filename
        linenum = _test.__code__.co_firstlineno
        expected = {'file.name': filename, 'line.number': linenum}
        unexpected = []

    _test = validate_span_events(
        count=count,
        exact_agents=expected,
        unexpected_agents=unexpected)(_test)

    _test()


@pytest.mark.parametrize('test_default', (True, False))
def test_span_event_web_transaction_task_default_attributes(test_default):
    override_settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    @override_application_settings(override_settings)
    @web_transaction(
        name="test_span_event_web_transaction_task_default_attributes"
    )
    def _test():
        transaction = current_transaction()
        transaction.queue_start = 1.0
        transaction._sampled = True

    if test_default:
        count = 1
        expected = {}
        unexpected = ['file.name', 'line.number']
    else:
        count = 1
        override_settings['attributes.include'] = ['file.name', 'line.number']
        filename = _test.__code__.co_filename
        linenum = _test.__code__.co_firstlineno
        expected = {'file.name': filename, 'line.number': linenum}
        unexpected = []

    _test = validate_span_events(
        count=count,
        exact_agents=expected,
        unexpected_agents=unexpected)(_test)

    _test()
