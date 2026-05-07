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
from newrelic.common.encoding_utils import NrTraceState, W3CTraceParent, W3CTraceState


def _single_value(value):
    if isinstance(value, list):
        assert len(value) == 1, value
        assert isinstance(value[0], str)
        return value[0]
    return value


def validate_distributed_tracing_header():
    transaction = current_transaction()
    headers = transaction._test_request_headers
    account_id = transaction.settings.account_id
    application_id = transaction.settings.primary_application_id
    trusted_account_key = transaction.settings.trusted_account_key or account_id

    assert "traceparent" in headers, headers
    assert "tracestate" in headers, headers

    traceparent = _single_value(headers["traceparent"])
    tracestate = _single_value(headers["tracestate"])

    # Parse traceparent (version-trace_id-parent_id-flags)
    w3c_parent = W3CTraceParent.decode(traceparent)
    assert w3c_parent is not None, traceparent

    trace_id = w3c_parent["tr"]
    assert len(trace_id) == 32
    assert trace_id.startswith(transaction.guid)

    # Parse tracestate, locate the New Relic vendor entry, decode it
    vendor_key = f"{trusted_account_key}@nr"
    vendors = W3CTraceState.decode(tracestate)
    assert vendor_key in vendors, tracestate

    data = NrTraceState.decode(vendors[vendor_key], trusted_account_key)
    assert data is not None, tracestate

    # Type will always be App (not mobile / browser)
    assert data["ty"] == "App"

    # Verify account/app id
    assert data["ac"] == account_id
    assert data["ap"] == application_id

    # Verify data belonging to this transaction
    assert data["tx"] == transaction.guid

    # If span events are enabled, id should be sent
    # otherwise, id should be omitted
    if transaction.settings.span_events.enabled:
        assert "id" in data
        assert data["id"] == w3c_parent["id"]
    else:
        assert "id" not in data

    # Verify timestamp is an integer
    assert isinstance(data["ti"], int)

    # Verify that priority is a float
    assert isinstance(data["pr"], float)

    # Sampled flag should agree between traceparent and tracestate
    assert data["sa"] == w3c_parent["sa"]
