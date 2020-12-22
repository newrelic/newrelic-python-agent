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

import json
import pytest
from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction, current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.encoding_utils import (
        DistributedTracePayload, W3CTraceParent, W3CTraceState, NrTraceState)

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)
from testing_support.validators.validate_span_events import (
        validate_span_events)
from _test_common import create_request, wait_for_transaction_completion


_test_matrix = ('method_name,streaming_request', (
    ('DoUnaryUnary', False),
    ('DoUnaryStream', False),
    ('DoStreamUnary', True),
    ('DoStreamStream', True)
))


@override_application_settings({'distributed_tracing.enabled': True})
@pytest.mark.parametrize(*_test_matrix)
def test_inbound_distributed_trace(mock_grpc_server, method_name,
        streaming_request, stub):
    request = create_request(streaming_request)

    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    @validate_transaction_metrics(
        'sample_application:SampleApplicationServicer.' + method_name,
        rollup_metrics=(
            ('Supportability/TraceContext/Accept/Success', 1),
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


@pytest.mark.parametrize(*_test_matrix)
@pytest.mark.parametrize('dt_enabled,dt_error', (
    (True, False),
    (True, True),
    (False, False),
))
def test_outbound_distributed_trace(
        mock_grpc_server, method_type, method_name, dt_enabled, dt_error, stub):
    request_type, response_type = method_type.split('_', 1)
    streaming_request = request_type == 'stream'
    streaming_response = response_type == 'stream'
    stub_method = 'DtNoTxn' + method_type.title().replace('_', '')

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

        metadata = json.loads(reply[0].text)

        if not dt_enabled or dt_error:
            assert 'newrelic' not in metadata
            assert 'traceparent' not in metadata
            assert 'tracestate' not in metadata
        else:
            decoded = DistributedTracePayload.decode(metadata['newrelic'])

            # The external span should be the parent
            exact_intrinsics['guid'] = decoded['d']['id']

            # Check that tracestate / traceparent payload matches newrelic
            # payload
            w3c_data = W3CTraceParent.decode(metadata['traceparent'])
            nr_tracestate = list(W3CTraceState.decode(
                    metadata['tracestate']).values())[0]
            nr_tracestate = NrTraceState.decode(nr_tracestate, None)
            w3c_data.update(nr_tracestate)

            # Remove all trust keys
            decoded['d'].pop('tk', None)
            w3c_data.pop('tk')

            assert decoded['d'] == w3c_data

    _test()


@pytest.mark.parametrize(*_test_matrix)
def test_outbound_payload_outside_transaction(
        mock_grpc_server, method_type, method_name, stub):
    request_type, response_type = method_type.split('_', 1)
    streaming_request = request_type == 'stream'
    streaming_response = response_type == 'stream'
    stub_method = 'DtNoTxn' + method_type.title().replace('_', '')

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
    metadata = json.loads(reply[0].text)

    assert 'newrelic' not in metadata
    assert 'traceparent' not in metadata
    assert 'tracestate' not in metadata
