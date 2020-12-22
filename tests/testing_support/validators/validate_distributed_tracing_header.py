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


from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import DistributedTracePayload

OUTBOUND_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'tr', 'pr', 'sa', 'ti')


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
