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

import random
import pytest
import six
import tempfile
import time

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)
from newrelic.core.config import global_settings, finalize_application_settings
from testing_support.fixtures import (override_generic_settings,
        function_not_called, failing_endpoint)

from newrelic.common.agent_http import DeveloperModeClient
from newrelic.core.application import Application
from newrelic.core.stats_engine import CustomMetrics, SampledDataSet
from newrelic.core.transaction_node import TransactionNode
from newrelic.core.root_node import RootNode
from newrelic.core.custom_event import create_custom_event
from newrelic.core.error_node import ErrorNode
from newrelic.core.function_node import FunctionNode

from newrelic.network.exceptions import RetryDataForRequest, ForceAgentDisconnect

settings = global_settings()


@pytest.fixture(scope='module')
def transaction_node(request):
    default_capacity = SampledDataSet().capacity
    num_events = default_capacity + 1

    custom_events = SampledDataSet(capacity=num_events)
    for _ in range(num_events):
        event = create_custom_event('Custom', {})
        custom_events.add(event)

    error = ErrorNode(
            timestamp=0,
            type='foo:bar',
            message='oh no! your foo had a bar',
            expected=False,
            span_id=None,
            stack_trace='',
            custom_params={},
            file_name=None,
            line_number=None,
            source=None)

    errors = tuple(error for _ in range(num_events))

    function = FunctionNode(
            group='Function',
            name='foo',
            children=(),
            start_time=0,
            end_time=1,
            duration=1,
            exclusive=1,
            label=None,
            params=None,
            rollup=None,
            guid='GUID',
            agent_attributes={},
            user_attributes={},)

    children = tuple(function for _ in range(num_events))

    root = RootNode(
            name='Function/main',
            children=children,
            start_time=1524764430.0,
            end_time=1524764430.1,
            duration=0.1,
            exclusive=0.1,
            guid=None,
            agent_attributes={},
            user_attributes={},
            path='OtherTransaction/Function/main',
            trusted_parent_span=None,
            tracing_vendors=None,
    )

    node = TransactionNode(
            settings=finalize_application_settings(
                    {'agent_run_id': '1234567'}),
            path='OtherTransaction/Function/main',
            type='OtherTransaction',
            group='Function',
            base_name='main',
            name_for_metric='Function/main',
            port=None,
            request_uri=None,
            queue_start=0.0,
            start_time=1524764430.0,
            end_time=1524764430.1,
            last_byte_time=0.0,
            total_time=0.1,
            response_time=0.1,
            duration=0.1,
            exclusive=0.1,
            root=root,
            errors=errors,
            slow_sql=(),
            custom_events=custom_events,
            apdex_t=0.5,
            suppress_apdex=False,
            custom_metrics=CustomMetrics(),
            guid='4485b89db608aece',
            cpu_time=0.0,
            suppress_transaction_trace=False,
            client_cross_process_id=None,
            referring_transaction_guid=None,
            record_tt=False,
            synthetics_resource_id=None,
            synthetics_job_id=None,
            synthetics_monitor_id=None,
            synthetics_header=None,
            is_part_of_cat=False,
            trip_id='4485b89db608aece',
            path_hash=None,
            referring_path_hash=None,
            alternate_path_hashes=[],
            trace_intrinsics={},
            distributed_trace_intrinsics={},
            agent_attributes=[],
            user_attributes=[],
            priority=1.0,
            parent_transport_duration=None,
            parent_span=None,
            parent_type=None,
            parent_account=None,
            parent_app=None,
            parent_tx=None,
            parent_transport_type=None,
            sampled=True,
            root_span_guid=None,
            trace_id='4485b89db608aece',
            loop_time=0.0,
    )
    return node


def validate_metric_payload(metrics=[], endpoints_called=[]):

    sent_metrics = {}

    @transient_function_wrapper('newrelic.core.agent_protocol',
            'AgentProtocol.send')
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(method, payload=(), *args, **kwargs):
            return method, payload

        method, payload = _bind_params(*args, **kwargs)
        endpoints_called.append(method)

        if method == 'metric_data' and payload:
            for metric_info, metric_values in payload[3]:
                metric_key = (metric_info['name'], metric_info['scope'])
                sent_metrics[metric_key] = metric_values

        return wrapped(*args, **kwargs)

    @function_wrapper
    def _wrapper(wrapped, instance, args, kwargs):

        def validate():
            for metric_name, count in metrics:
                metric_key = (metric_name, '')  # only search unscoped

                if count is not None:
                    assert metric_key in sent_metrics, metric_key
                    assert sent_metrics[metric_key][0] == count, metric_key
                else:
                    assert metric_key not in sent_metrics, metric_key

        _new_wrapper = send_request_wrapper(wrapped)
        val = _new_wrapper(*args, **kwargs)
        validate()
        return val

    return _wrapper


def validate_transaction_event_payloads(payload_validators):

    @function_wrapper
    def _wrapper(wrapped, instance, args, kwargs):

        payloads = []

        @transient_function_wrapper('newrelic.core.agent_protocol',
                'AgentProtocol.send')
        def send_request_wrapper(wrapped, instance, args, kwargs):
            def _bind_params(method, payload=(), *args, **kwargs):
                return method, payload

            method, payload = _bind_params(*args, **kwargs)

            if method == 'analytic_event_data':
                payloads.append(payload)

            return wrapped(*args, **kwargs)

        _new_wrapper = send_request_wrapper(wrapped)
        val = _new_wrapper(*args, **kwargs)

        assert len(payloads) == len(payload_validators)

        for payload, validator in zip(payloads, payload_validators):
            validator(payload)

        return val

    return _wrapper


def validate_error_event_sampling(events_seen, reservoir_size,
        endpoints_called=[]):

    @transient_function_wrapper('newrelic.core.data_collector',
            'AgentProtocol.send')
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(method, payload=(), *args, **kwargs):
            return method, payload

        method, payload = _bind_params(*args, **kwargs)
        endpoints_called.append(method)

        if method == 'error_event_data':
            sampling_info = payload[1]
            assert sampling_info['events_seen'] == events_seen
            assert sampling_info['reservoir_size'] == reservoir_size

        return wrapped(*args, **kwargs)

    return send_request_wrapper


required_metrics = [
    ('Supportability/Events/TransactionError/Seen', 0),
    ('Supportability/Events/TransactionError/Sent', 0),
    ('Supportability/Events/Customer/Seen', 0),
    ('Supportability/Events/Customer/Sent', 0),
    ('Supportability/Python/RequestSampler/requests', 1),
    ('Supportability/Python/RequestSampler/samples', 1),
    ('Instance/Reporting', 1),
]

endpoints_called = []


@validate_metric_payload(metrics=required_metrics,
        endpoints_called=endpoints_called)
@override_generic_settings(settings, {
    'developer_mode': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
    'audit_log_file': tempfile.NamedTemporaryFile().name,
})
def test_application_harvest():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)
    app.harvest()

    # Verify that the metric_data endpoint is the 2nd to last endpoint called
    # Last endpoint called is get_agent_commands
    assert endpoints_called[-2] == 'metric_data'

    # verify audit log is not empty
    with open(settings.audit_log_file, 'rb') as f:
        assert f.read()


@override_generic_settings(settings, {
    'serverless_mode.enabled': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
    'audit_log_file': tempfile.NamedTemporaryFile().name,
})
def test_serverless_application_harvest():
    app = Application('Python Agent Test (Serverless Harvest Loop)')
    app.connect_to_data_collector(None)
    app.harvest()

    # verify audit log is not empty
    with open(settings.audit_log_file, 'rb') as f:
        assert f.read()


@pytest.mark.parametrize(
    'distributed_tracing_enabled,span_events_enabled,spans_created', [
        (True, True, 1),
        (True, True, 15),
        (True, False, 1),
        (True, True, 0),
        (True, False, 0),
        (False, True, 0),
])
def test_application_harvest_with_spans(distributed_tracing_enabled,
        span_events_enabled, spans_created):

    span_endpoints_called = []
    max_samples_stored = 10

    if distributed_tracing_enabled and span_events_enabled:
        seen = spans_created
        sent = min(spans_created, max_samples_stored)
    else:
        seen = None
        sent = None

    spans_required_metrics = list(required_metrics)

    spans_required_metrics.extend([
        ('Supportability/SpanEvent/TotalEventsSeen', seen),
        ('Supportability/SpanEvent/TotalEventsSent', sent),
    ])

    @validate_metric_payload(metrics=spans_required_metrics,
            endpoints_called=span_endpoints_called)
    @override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
        'distributed_tracing.enabled': distributed_tracing_enabled,
        'span_events.enabled': span_events_enabled,
        'event_harvest_config.harvest_limits.span_event_data':
            max_samples_stored,
    })
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        for _ in range(spans_created):
            app._stats_engine.span_events.add('event')

        assert app._stats_engine.span_events.num_samples == (
                min(spans_created, max_samples_stored))
        app.harvest()
        assert app._stats_engine.span_events.num_samples == 0

        # Verify that the metric_data endpoint is the 2nd to last and
        # span_event_data is the 3rd to last endpoint called
        assert span_endpoints_called[-2] == 'metric_data'

        if span_events_enabled and spans_created > 0:
            assert span_endpoints_called[-3] == 'span_event_data'
        else:
            assert span_endpoints_called[-3] != 'span_event_data'

    _test()


@pytest.mark.parametrize(
    'span_queue_size, spans_to_send, expected_seen, expected_sent', (
    (0, 1, 1, 0),
    (1, 1, 1, 1),
    (7, 10, 10, 7),
))
def test_application_harvest_with_span_streaming(span_queue_size,
        spans_to_send, expected_sent, expected_seen):

    @override_generic_settings(settings, {
        'developer_mode': True,
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'infinite_tracing._trace_observer_host': 'x',
        'infinite_tracing.span_queue_size': span_queue_size,
    })
    @validate_metric_payload(metrics=[
        ('Supportability/InfiniteTracing/Span/Seen', expected_seen),
        ('Supportability/InfiniteTracing/Span/Sent', expected_sent),
    ], endpoints_called=[])
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        for _ in range(spans_to_send):
            app._stats_engine.span_stream.put(None)
        app.harvest()

    _test()


@failing_endpoint('metric_data')
@pytest.mark.parametrize('span_events_enabled', (True, False))
def test_failed_spans_harvest(span_events_enabled):

    @override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
        'distributed_tracing.enabled': True,
        'span_events.enabled': span_events_enabled,
    })
    def _test():
        # Test that if an endpoint call that occurs after we successfully send
        # span data fails, we do not try to send span data again with the next
        # harvest.

        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        app._stats_engine.span_events.add('event')
        assert app._stats_engine.span_events.num_samples == 1
        app.harvest()
        assert app._stats_engine.span_events.num_samples == 0

    _test()


@override_generic_settings(settings, {
    'developer_mode': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
    'collect_custom_events': False,
})
def test_transaction_count(transaction_node):
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    app.record_transaction(transaction_node)

    # Harvest has not run yet
    assert app._transaction_count == 1

    app.harvest()

    # Harvest resets the transaction count
    assert app._transaction_count == 0

    # Record a transaction
    app.record_transaction(transaction_node)
    assert app._transaction_count == 1

    app.harvest()

    # Harvest resets the transaction count
    assert app._transaction_count == 0


@override_generic_settings(settings, {
    'developer_mode': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
})
def test_adaptive_sampling(transaction_node, monkeypatch):
    app = Application('Python Agent Test (Harvest Loop)')

    # Should always return false for sampling prior to connect
    assert app.compute_sampled() is False

    app.connect_to_data_collector(None)

    # First harvest, first N should be sampled
    for _ in range(settings.sampling_target):
        assert app.compute_sampled() is True

    assert app.compute_sampled() is False

    # fix random.randrange to return 0
    monkeypatch.setattr(random, 'randrange', lambda *args, **kwargs: 0)

    # Multiple resets should behave the same
    for _ in range(2):
        # Set the last_reset to longer than the period so a reset will occur.
        app.adaptive_sampler.last_reset = \
            time.time() - app.adaptive_sampler.period

        # Subsequent harvests should allow sampling of 2X the target
        for _ in range(2 * settings.sampling_target):
            assert app.compute_sampled() is True

        # No further samples should be saved
        assert app.compute_sampled() is False


@override_generic_settings(settings, {
    'developer_mode': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
    'distributed_tracing.enabled': True,
    'event_harvest_config.harvest_limits.error_event_data': 1000,
    'event_harvest_config.harvest_limits.span_event_data': 1000,
    'event_harvest_config.harvest_limits.custom_event_data': 1000,
})
def test_reservoir_sizes(transaction_node):
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    # Record a transaction with events
    app.record_transaction(transaction_node)

    # Test that the samples have been recorded
    assert app._stats_engine.custom_events.num_samples == 101
    assert app._stats_engine.error_events.num_samples == 101

    # Add 1 for the root span
    assert app._stats_engine.span_events.num_samples == 102


@pytest.mark.parametrize('harvest_name, event_name', [
    ('analytic_event_data', 'transaction_events'),
    ('error_event_data', 'error_events'),
    ('custom_event_data', 'custom_events'),
    ('span_event_data', 'span_events')
])
@override_generic_settings(settings, {
    'developer_mode': True,
    'license_key': '**NOT A LICENSE KEY**',
    'feature_flag': set(),
    'distributed_tracing.enabled': True,
})
def test_reservoir_size_zeros(harvest_name, event_name):
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    setattr(settings.event_harvest_config.harvest_limits, harvest_name, 0)
    settings.event_harvest_config.whitelist = frozenset(())
    app._stats_engine.reset_stats(settings)

    app._stats_engine.transaction_events.add('transaction event')
    app._stats_engine.error_events.add('error event')
    app._stats_engine.custom_events.add('custom event')
    app._stats_engine.span_events.add('span event')

    assert app._stats_engine.transaction_events.num_seen == 1
    assert app._stats_engine.error_events.num_seen == 1
    assert app._stats_engine.custom_events.num_seen == 1
    assert app._stats_engine.span_events.num_seen == 1

    stat_events = set(('transaction_events', 'error_events', 'custom_events',
    'span_events'))

    for stat_event in stat_events:
        event = getattr(app._stats_engine, stat_event)

        if stat_event == event_name:
            assert event.num_samples == 0
        else:
            assert event.num_samples == 1

    app.harvest()

    assert app._stats_engine.transaction_events.num_seen == 0
    assert app._stats_engine.error_events.num_seen == 0
    assert app._stats_engine.custom_events.num_seen == 0
    assert app._stats_engine.span_events.num_seen == 0


@pytest.mark.parametrize('events_seen', (1, 5, 10))
def test_error_event_sampling_info(events_seen):

    reservoir_size = 5
    endpoints_called = []

    @validate_error_event_sampling(
            events_seen=events_seen,
            reservoir_size=reservoir_size,
            endpoints_called=endpoints_called)
    @override_generic_settings(settings, {
            'developer_mode': True,
            'license_key': '**NOT A LICENSE KEY**',
            'event_harvest_config.harvest_limits.error_event_data':
            reservoir_size,
    })
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        for _ in range(events_seen):
            app._stats_engine.error_events.add('error')

        app.harvest()

    _test()
    assert 'error_event_data' in endpoints_called


@pytest.mark.parametrize(
'time_to_next_reset,computed_count,computed_count_last', (
    (20, 124, 10),  # no reset
    (-8, 1, 123),   # reset to last transaction count
    (-68, 1, 10),   # more than 1 minute passed, reset fully
))
@override_generic_settings(settings, {
        'serverless_mode.enabled': True,
})
def test_serverless_mode_adaptive_sampling(time_to_next_reset,
        computed_count, computed_count_last, monkeypatch):
    # fix random.randrange to return 0
    monkeypatch.setattr(random, 'randrange', lambda *args, **kwargs: 0)

    app = Application('Python Agent Test (Harvest Loop)')

    app.connect_to_data_collector(None)
    app.adaptive_sampler.computed_count = 123
    app.adaptive_sampler.last_reset = time.time() - 60 + time_to_next_reset

    assert app.compute_sampled() is True
    assert app.adaptive_sampler.computed_count == computed_count
    assert app.adaptive_sampler.computed_count_last == computed_count_last


@function_not_called(
        'newrelic.core.adaptive_sampler', 'AdaptiveSampler._reset')
@override_generic_settings(settings, {
        'developer_mode': True,
})
def test_compute_sampled_no_reset():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)
    assert app.compute_sampled() is True


def test_analytic_event_sampling_info():

    synthetics_limit = 10
    transactions_limit = 20

    def synthetics_validator(payload):
        _, sampling_info, _ = payload
        assert sampling_info['reservoir_size'] == synthetics_limit
        assert sampling_info['events_seen'] == 1

    def transactions_validator(payload):
        _, sampling_info, _ = payload
        assert sampling_info['reservoir_size'] == transactions_limit
        assert sampling_info['events_seen'] == 1

    validators = [synthetics_validator, transactions_validator]

    @validate_transaction_event_payloads(validators)
    @override_generic_settings(settings, {
            'developer_mode': True,
            'event_harvest_config.harvest_limits.analytic_event_data':
            transactions_limit,
            'agent_limits.synthetics_events': synthetics_limit,
    })
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        app._stats_engine.transaction_events.add('transaction event')
        app._stats_engine.synthetics_events.add('synthetic event')

        app.harvest()

    _test()


@pytest.mark.parametrize('has_synthetic_events', (True, False))
@pytest.mark.parametrize('has_transaction_events', (True, False))
@override_generic_settings(settings, {
        'developer_mode': True,
})
def test_analytic_event_payloads(has_synthetic_events, has_transaction_events):

    def synthetics_validator(payload):
        events = payload[-1]
        assert list(events) == ['synthetic event']

    def transactions_validator(payload):
        events = payload[-1]
        assert list(events) == ['transaction event']

    validators = []
    if has_synthetic_events:
        validators.append(synthetics_validator)
    if has_transaction_events:
        validators.append(transactions_validator)

    @validate_transaction_event_payloads(validators)
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)

        if has_transaction_events:
            app._stats_engine.transaction_events.add('transaction event')

        if has_synthetic_events:
            app._stats_engine.synthetics_events.add('synthetic event')

        app.harvest()

    _test()


@override_generic_settings(settings, {
        'developer_mode': True,
        'collect_analytics_events': False,
        'transaction_events.enabled': False,
})
def test_transaction_events_disabled():

    endpoints_called = []
    expected_metrics = (
            ('Supportability/Python/RequestSampler/requests', None),
            ('Supportability/Python/RequestSampler/samples', None),
    )

    @validate_metric_payload(expected_metrics, endpoints_called)
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)
        app.harvest()

    _test()
    assert 'metric_data' in endpoints_called


@failing_endpoint('analytic_event_data', call_number=2)
@override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
})
def test_reset_synthetics_events():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    app._stats_engine.synthetics_events.add('synthetics event')
    app._stats_engine.transaction_events.add('transaction event')

    assert app._stats_engine.synthetics_events.num_seen == 1
    assert app._stats_engine.transaction_events.num_seen == 1

    app.harvest()

    assert app._stats_engine.synthetics_events.num_seen == 0
    assert app._stats_engine.transaction_events.num_seen == 1


@pytest.mark.parametrize('whitelist_event', ('analytic_event_data',
    'custom_event_data', 'error_event_data', 'span_event_data'))
@override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
})
def test_flexible_events_harvested(whitelist_event):
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    settings.event_harvest_config.whitelist = frozenset((whitelist_event,))
    app._stats_engine.reset_stats(settings)

    app._stats_engine.transaction_events.add('transaction event')
    app._stats_engine.error_events.add('error event')
    app._stats_engine.custom_events.add('custom event')
    app._stats_engine.span_events.add('span event')
    app._stats_engine.record_custom_metric('CustomMetric/Int', 1)

    assert app._stats_engine.transaction_events.num_seen == 1
    assert app._stats_engine.error_events.num_seen == 1
    assert app._stats_engine.custom_events.num_seen == 1
    assert app._stats_engine.span_events.num_seen == 1
    assert app._stats_engine.record_custom_metric('CustomMetric/Int', 1)

    app.harvest(flexible=True)

    num_seen = 0 if (whitelist_event == 'analytic_event_data') else 1
    assert app._stats_engine.transaction_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event == 'error_event_data') else 1
    assert app._stats_engine.error_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event == 'custom_event_data') else 1
    assert app._stats_engine.custom_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event == 'span_event_data') else 1
    assert app._stats_engine.span_events.num_seen == num_seen

    assert ('CustomMetric/Int', '') in app._stats_engine.stats_table
    assert app._stats_engine.metrics_count() > 1


@pytest.mark.parametrize('whitelist_event', ('analytic_event_data',
    'custom_event_data', 'error_event_data', 'span_event_data'))
@override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
})
def test_default_events_harvested(whitelist_event):
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    settings.event_harvest_config.whitelist = frozenset((whitelist_event,))
    app._stats_engine.reset_stats(settings)

    app._stats_engine.transaction_events.add('transaction event')
    app._stats_engine.error_events.add('error event')
    app._stats_engine.custom_events.add('custom event')
    app._stats_engine.span_events.add('span event')

    assert app._stats_engine.transaction_events.num_seen == 1
    assert app._stats_engine.error_events.num_seen == 1
    assert app._stats_engine.custom_events.num_seen == 1
    assert app._stats_engine.span_events.num_seen == 1
    assert app._stats_engine.metrics_count() == 0

    app.harvest(flexible=False)

    num_seen = 0 if (whitelist_event != 'analytic_event_data') else 1
    assert app._stats_engine.transaction_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event != 'error_event_data') else 1
    assert app._stats_engine.error_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event != 'custom_event_data') else 1
    assert app._stats_engine.custom_events.num_seen == num_seen

    num_seen = 0 if (whitelist_event != 'span_event_data') else 1
    assert app._stats_engine.span_events.num_seen == num_seen

    assert app._stats_engine.metrics_count() == 1


@failing_endpoint('analytic_event_data')
@override_generic_settings(settings, {
        'developer_mode': True,
        'agent_limits.merge_stats_maximum': 0,
})
def test_infinite_merges():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    app._stats_engine.transaction_events.add('transaction event')

    assert app._stats_engine.transaction_events.num_seen == 1

    app.harvest()

    # the agent_limits.merge_stats_maximum is not respected
    assert app._stats_engine.transaction_events.num_seen == 1


@failing_endpoint('analytic_event_data')
@override_generic_settings(settings, {
        'developer_mode': True,
})
def test_flexible_harvest_rollback():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)

    settings.event_harvest_config.whitelist = frozenset(
            ('analytic_event_data',))
    app._stats_engine.reset_stats(settings)

    # Cause a transaction event to attempt sending
    app._stats_engine.transaction_events.add(
            'Custom/test_flexible_harvest_rollback')

    # Add a metric to the stats engine
    app._stats_engine.record_custom_metric(
            'Custom/test_flexible_harvest_rollback', 1)
    stats_key = ('Custom/test_flexible_harvest_rollback', '')
    assert stats_key in app._stats_engine.stats_table

    app.harvest(flexible=True)

    # The metric should not be changed after a rollback
    assert app._stats_engine.stats_table[stats_key].call_count == 1


@override_generic_settings(settings, {
        'developer_mode': True,
})
def test_get_agent_commands_returns_none():
    MISSING = object()
    original_return_value = DeveloperModeClient.RESPONSES.get('get_agent_commands', MISSING)
    DeveloperModeClient.RESPONSES['get_agent_commands'] = None

    try:
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector(None)
        app.process_agent_commands()
    finally:
        if original_return_value is MISSING:
            DeveloperModeClient.RESPONSES.pop('get_agent_commands')
        else:
            DeveloperModeClient.RESPONSES['get_agent_commands'] = original_return_value


@failing_endpoint('get_agent_commands')
@override_generic_settings(settings, {
        'developer_mode': True,
})
def test_get_agent_commands_raises():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector(None)
    with pytest.raises(RetryDataForRequest):
        app.process_agent_commands()
