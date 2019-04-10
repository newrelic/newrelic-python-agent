import pytest
from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction, current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.encoding_utils import DistributedTracePayload

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)
from testing_support.validators.validate_span_events import (
        validate_span_events)
from _test_common import (create_stub, create_request,
        wait_for_transaction_completion)


_test_matrix = ('method_name,streaming_request', (
    ('DoUnaryUnary', False),
    ('DoUnaryStream', False),
    ('DoStreamUnary', True),
    ('DoStreamStream', True)
))


@override_application_settings({'distributed_tracing.enabled': True})
@pytest.mark.parametrize(*_test_matrix)
def test_inbound_distributed_trace(mock_grpc_server, method_name,
        streaming_request):
    stub = create_stub(mock_grpc_server)
    request = create_request(streaming_request)

    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    @validate_transaction_metrics(
        'sample_application:SampleApplicationServicer.' + method_name,
        rollup_metrics=(
            ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
        ),
    )
    @wait_for_transaction_completion
    def _test():
        method = getattr(stub, method_name)
        response = method(request, metadata=dt_headers)

        try:
            list(response)
        except Exception:
            pass

    _test()


_test_matrix = ('method_type,method_name', (
        ('unary_unary', '__call__'),
        ('unary_unary', 'with_call'),
        ('stream_unary', '__call__'),
        ('stream_unary', 'with_call'),
        ('unary_stream', '__call__'),
        ('stream_stream', '__call__'),
))


@pytest.mark.xfail()
@pytest.mark.parametrize(*_test_matrix)
@pytest.mark.parametrize('dt_enabled,dt_error', (
    (True, False),
    (True, True),
    (False, False),
))
def test_outbound_distributed_trace(
        mock_grpc_server, method_type, method_name, dt_enabled, dt_error):
    stub = create_stub(mock_grpc_server)
    request_type, response_type = method_type.split('_', 1)
    streaming_request = request_type == 'stream'
    streaming_response = response_type == 'stream'
    stub_method = 'Dt' + method_type.title().replace('_', '')

    request = create_request(streaming_request)

    method_callable = getattr(stub, stub_method)
    method = getattr(method_callable, method_name)

    exact_intrinsics = {
        'category': 'http',
        'span.kind': 'client',
    }

    txn_name = 'test_outbound_DT[{0}-{1}-{2}-{3}]'.format(
            method_type, method_name, dt_enabled, dt_error)
    settings = {'distributed_tracing.enabled': dt_enabled}
    span_count = 1 if dt_enabled else 0
    if dt_error:
        settings['trusted_account_key'] = None

    @override_application_settings(settings)
    @validate_span_events(count=span_count, exact_intrinsics=exact_intrinsics)
    @wait_for_transaction_completion
    @background_task(name=txn_name)
    def _test():
        # Always mark sampled as True. current_transaction() is guaranteed to
        # be non-None here as test fixtures ensure activation prior to testing.
        current_transaction()._sampled = True

        reply = method(request)

        if isinstance(reply, tuple):
            reply = reply[0]

        try:
            # If the reply was canceled or the server code raises an exception,
            # this will raise an exception which will be recorded by the agent
            if streaming_response:
                reply = list(reply)
            else:
                reply = [reply.result()]
        except (AttributeError, TypeError):
            reply = [reply]

        if not dt_enabled or dt_error:
            assert not reply[0].text
        else:
            decoded = DistributedTracePayload.decode(reply[0].text)

            # The external span should be the parent
            exact_intrinsics['guid'] = decoded['d']['id']

    _test()


@pytest.mark.parametrize(*_test_matrix)
def test_outbound_payload_outside_transaction(
        mock_grpc_server, method_type, method_name):
    stub = create_stub(mock_grpc_server)
    request_type, response_type = method_type.split('_', 1)
    streaming_request = request_type == 'stream'
    streaming_response = response_type == 'stream'
    stub_method = 'Dt' + method_type.title().replace('_', '')

    request = create_request(streaming_request)

    method_callable = getattr(stub, stub_method)
    method = getattr(method_callable, method_name)

    reply = method(request)

    if isinstance(reply, tuple):
        reply = reply[0]

    try:
        # If the reply was canceled or the server code raises an exception,
        # this will raise an exception which will be recorded by the agent
        if streaming_response:
            reply = list(reply)
        else:
            reply = [reply.result()]
    except (AttributeError, TypeError):
        reply = [reply]

    # Verify there were no DT headers sent
    assert not reply[0].text
