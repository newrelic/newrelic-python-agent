import pytest

from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.config import global_settings, finalize_application_settings
from testing_support.fixtures import override_generic_settings

from newrelic.core.application import Application
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.transaction_node import TransactionNode

from newrelic.network.exceptions import RetryDataForRequest
settings = global_settings()


@pytest.fixture(scope='module')
def transaction_node():
    node = TransactionNode(
            settings=finalize_application_settings({'agent_run_id': 1234567}),
            path='OtherTransaction/Function/main',
            type='OtherTransaction',
            group='Function',
            base_name='main',
            name_for_metric='Function/main',
            port=None,
            request_uri=None,
            response_code=0,
            queue_start=0.0,
            start_time=1524764430.0,
            end_time=1524764430.1,
            last_byte_time=0.0,
            total_time=0.1,
            response_time=0.1,
            duration=0.1,
            exclusive=0.1,
            children=(),
            errors=(),
            slow_sql=(),
            custom_events=None,
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
    )
    return node


def validate_metric_payload(metrics=[], endpoints_called=[]):
    @transient_function_wrapper('newrelic.core.data_collector',
            'DeveloperModeSession.send_request')
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(session, url, method, license_key,
                agent_run_id=None, payload=(), *args, **kwargs):
            return method, payload

        method, payload = _bind_params(*args, **kwargs)
        endpoints_called.append(method)

        if method == 'metric_data' and payload:
            sent_metrics = {}
            for metric_info, metric_values in payload[3]:
                metric_key = (metric_info['name'], metric_info['scope'])
                sent_metrics[metric_key] = metric_values

            for metric_name, count in metrics:
                metric_key = (metric_name, '')  # only search unscoped

                if count is not None:
                    assert metric_key in sent_metrics, metric_key
                    assert sent_metrics[metric_key][0] == count, metric_key
                else:
                    assert metric_key not in sent_metrics, metric_key

        return wrapped(*args, **kwargs)

    return send_request_wrapper


def failing_endpoint(endpoint, raises=RetryDataForRequest):
    @transient_function_wrapper('newrelic.core.data_collector',
            'DeveloperModeSession.send_request')
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(session, url, method, license_key,
                agent_run_id=None, payload=(), *args, **kwargs):
            return method

        method = _bind_params(*args, **kwargs)

        if method == endpoint:
            raise raises()

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
})
def test_application_harvest():
    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector()
    app.harvest()

    # Verify that the metric_data endpoint is the 2nd to last endpoint called
    # Last endpoint called is get_agent_commands
    assert endpoints_called[-2] == 'metric_data'


@pytest.mark.parametrize(
    'span_events_enabled,spans_created', [
        (True, 1),
        (True, 15),
        (False, 1),
])
def test_application_harvest_with_spans(span_events_enabled, spans_created):

    span_endpoints_called = []
    max_samples_stored = 10

    if span_events_enabled:
        seen = spans_created
        sent = min(spans_created, max_samples_stored)
        discarded = seen - sent
    else:
        seen = None
        sent = None
        discarded = None

    spans_required_metrics = list(required_metrics)

    spans_required_metrics.extend([
        ('Supportability/SpanEvent/TotalEventsSeen', seen),
        ('Supportability/SpanEvent/TotalEventsSent', sent),
        ('Supportability/SpanEvent/Discarded', discarded),
    ])

    @validate_metric_payload(metrics=spans_required_metrics,
            endpoints_called=span_endpoints_called)
    @override_generic_settings(settings, {
        'developer_mode': True,
        'license_key': '**NOT A LICENSE KEY**',
        'distributed_tracing.enabled': True,
        'span_events.enabled': span_events_enabled,
        'span_events.max_samples_stored': max_samples_stored,
    })
    def _test():
        app = Application('Python Agent Test (Harvest Loop)')
        app.connect_to_data_collector()

        for _ in range(spans_created):
            app._stats_engine.span_events.add('event')

        assert app._stats_engine.span_events.num_samples == (
                min(spans_created, max_samples_stored))
        app.harvest()
        assert app._stats_engine.span_events.num_samples == 0

        # Verify that the metric_data endpoint is the 2nd to last and
        # span_event_data is the 3rd to last endpoint called
        assert span_endpoints_called[-2] == 'metric_data'

        if span_events_enabled:
            assert span_endpoints_called[-3] == 'span_event_data'
        else:
            assert span_endpoints_called[-3] != 'span_event_data'

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
        app.connect_to_data_collector()

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
    app.connect_to_data_collector()

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
def test_adaptive_sampling(transaction_node):
    app = Application('Python Agent Test (Harvest Loop)')

    # Should always return false for sampling prior to connect
    assert app.compute_sampled(1.0) is False

    app.connect_to_data_collector()

    # First harvest, first N should be sampled
    for _ in range(settings.sampling_target):
        assert app.compute_sampled(1.0) is True

    assert app.compute_sampled(1.0) is False

    # Multiple harvests should behave the same
    for _ in range(2):
        app.harvest()

        # Subsequent harvests should allow sampling of 2X the target
        for _ in range(2 * settings.sampling_target):
            assert app.compute_sampled(1.0) is True

        # No further samples should be saved
        assert app.compute_sampled(1.0) is False
