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

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import (json_encode, json_decode,
    obfuscate, deobfuscate, DistributedTracePayload)
from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)

OUTBOUND_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'tr', 'pr', 'sa', 'ti')


def validate_outbound_headers(header_id='X-NewRelic-ID',
        header_transaction='X-NewRelic-Transaction'):
    transaction = current_transaction()
    headers = transaction._test_request_headers
    settings = transaction.settings
    encoding_key = settings.encoding_key

    assert header_id in headers

    values = headers[header_id]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    cross_process_id = deobfuscate(value, encoding_key)
    assert cross_process_id == settings.cross_process_id

    assert header_transaction in headers

    values = headers[header_transaction]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    (guid, record_tt, trip_id, path_hash) = \
            json_decode(deobfuscate(value, encoding_key))

    assert guid == transaction.guid
    assert record_tt == transaction.record_tt
    assert trip_id == transaction.trip_id
    assert path_hash == transaction.path_hash


def validate_distributed_tracing_header(header='newrelic'):
    transaction = current_transaction()
    headers = transaction._test_request_headers
    account_id = transaction.settings.account_id
    application_id = transaction.settings.primary_application_id

    assert header in headers, headers

    values = headers[header]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    # Parse payload
    payload = DistributedTracePayload.from_http_safe(value)

    # Distributed Tracing v0.1 is currently implemented
    assert payload['v'] == [0, 1], payload['v']

    data = payload['d']

    # Verify all required keys are present
    assert all(k in data for k in OUTBOUND_TRACE_KEYS_REQUIRED)

    # Type will always be App (not mobile / browser)
    assert data['ty'] == 'App'

    # Verify account/app id
    assert data['ac'] == account_id
    assert data['ap'] == application_id

    # Verify data belonging to this transaction
    assert data['tx'] == transaction.guid

    # If span events are enabled, id should be sent
    # otherwise, id should be omitted
    if transaction.settings.span_events.enabled:
        assert 'id' in data
    else:
        assert 'id' not in data

    # Verify referring transaction information
    assert len(data['tr']) == 32
    if transaction.referring_transaction_guid is not None:
        assert data['tr'] == transaction._trace_id
    else:
        assert data['tr'].startswith(transaction.guid)

    assert 'pa' not in data

    # Verify timestamp is an integer
    assert isinstance(data['ti'], int)

    # Verify that priority is a float
    assert isinstance(data['pr'], float)


@function_wrapper
def validate_cross_process_headers(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    transaction = current_transaction()
    settings = transaction.settings

    if settings.distributed_tracing.enabled:
        validate_distributed_tracing_header()
    else:
        validate_outbound_headers()

    return result

def create_incoming_headers(transaction):
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = []

    cross_process_id = '1#2'
    path = 'test'
    queue_time = 1.0
    duration = 2.0
    read_length = 1024
    guid = '0123456789012345'
    record_tt = False

    payload = (cross_process_id, path, queue_time, duration, read_length,
            guid, record_tt)
    app_data = json_encode(payload)

    value = obfuscate(app_data, encoding_key)

    assert isinstance(value, type(''))

    headers.append(('X-NewRelic-App-Data', value))

    return headers


def validate_external_node_params(params=[], forgone_params=[]):
    """
    Validate the parameters on the external node.

    params: a list of tuples
    forgone_params: a flat list
    """
    @transient_function_wrapper('newrelic.api.external_trace',
            'ExternalTrace.process_response_headers')
    def _validate_external_node_params(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # This is only validating that logic to extract cross process
        # header and update params in ExternalTrace is succeeding. This
        # is actually done after the ExternalTrace __exit__() is called
        # with the ExternalNode only being updated by virtue of the
        # original params dictionary being aliased rather than copied.
        # So isn't strictly validating that params ended up in the actual
        # ExternalNode in the transaction trace.

        for name, value in params:
            assert instance.params[name] == value

        for name in forgone_params:
            assert name not in instance.params

        return result

    return _validate_external_node_params

def validate_synthetics_external_trace_header(required_header=(),
        should_exist=True):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_synthetics_external_trace_header(wrapped, instance,
            args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            if should_exist:
                # XXX This validation routine is technically
                # broken as the argument to record_transaction()
                # is not actually an instance of the Transaction
                # object. Instead it is a TransactionNode object.
                # The static method generate_request_headers() is
                # expecting a Transaction object and not
                # TransactionNode. The latter provides attributes
                # which are not updatable by the static method
                # generate_request_headers(), which it wants to
                # update, so would fail. For now what we do is use
                # a little proxy wrapper so that updates do not
                # fail. The use of this wrapper needs to be
                # reviewed and a better way of achieving what is
                # required found.

                class _Transaction(object):
                    def __init__(self, wrapped):
                        self.__wrapped__ = wrapped

                    def __getattr__(self, name):
                        return getattr(self.__wrapped__, name)

                external_headers = ExternalTrace.generate_request_headers(
                        _Transaction(transaction))
                assert required_header in external_headers, (
                        'required_header=%r, ''external_headers=%r' % (
                        required_header, external_headers))

        return result

    return _validate_synthetics_external_trace_header

def validate_outbound_headers(header_id='X-NewRelic-ID',
        header_transaction='X-NewRelic-Transaction'):
    transaction = current_transaction()
    headers = transaction._test_request_headers
    settings = transaction.settings
    encoding_key = settings.encoding_key

    assert header_id in headers

    values = headers[header_id]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    cross_process_id = deobfuscate(value, encoding_key)
    assert cross_process_id == settings.cross_process_id

    assert header_transaction in headers

    values = headers[header_transaction]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    (guid, record_tt, trip_id, path_hash) = \
            json_decode(deobfuscate(value, encoding_key))

    assert guid == transaction.guid
    assert record_tt == transaction.record_tt
    assert trip_id == transaction.trip_id
    assert path_hash == transaction.path_hash


def validate_distributed_tracing_header(header='newrelic'):
    transaction = current_transaction()
    headers = transaction._test_request_headers
    account_id = transaction.settings.account_id
    application_id = transaction.settings.primary_application_id

    assert header in headers, headers

    values = headers[header]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    # Parse payload
    payload = DistributedTracePayload.from_http_safe(value)

    # Distributed Tracing v0.1 is currently implemented
    assert payload['v'] == [0, 1], payload['v']

    data = payload['d']

    # Verify all required keys are present
    assert all(k in data for k in OUTBOUND_TRACE_KEYS_REQUIRED)

    # Type will always be App (not mobile / browser)
    assert data['ty'] == 'App'

    # Verify account/app id
    assert data['ac'] == account_id
    assert data['ap'] == application_id

    # Verify data belonging to this transaction
    assert data['tx'] == transaction.guid

    # If span events are enabled, id should be sent
    # otherwise, id should be omitted
    if transaction.settings.span_events.enabled:
        assert 'id' in data
    else:
        assert 'id' not in data

    # Verify referring transaction information
    assert len(data['tr']) == 32
    if transaction.referring_transaction_guid is not None:
        assert data['tr'] == transaction._trace_id
    else:
        assert data['tr'].startswith(transaction.guid)

    assert 'pa' not in data

    # Verify timestamp is an integer
    assert isinstance(data['ti'], int)

    # Verify that priority is a float
    assert isinstance(data['pr'], float)

