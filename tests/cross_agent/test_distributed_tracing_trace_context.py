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

import base64
import json
from pathlib import Path

import pytest
import webtest
from testing_support.fixtures import override_application_settings, validate_attributes
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

import newrelic.agent
from newrelic.common.encoding_utils import (
    NrTraceState,
    W3CTraceParent,
    W3CTraceState,
    PARENT_TYPE
)
from newrelic.api.transaction import current_transaction
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.encoding_utils import DistributedTracePayload
from newrelic.common.object_wrapper import transient_function_wrapper

FIXTURE = Path(__file__).parent / "fixtures" / "distributed_tracing" / "trace_context.json"

def load_tests():
    result = []
    with FIXTURE.open(encoding="utf-8") as fh:
        tests = json.load(fh)

    for test in tests:
        _id = test.pop("test_name", None)
        test_desc = test.pop("comment", None)
        settings = {
            "distributed_tracing.sampler.full_granularity.enabled": test.pop("full_granularity_enabled", True),
            "distributed_tracing.enabled": test.pop("distributed_tracing_enabled", True),
            "span_events.enabled": test.pop("span_events_enabled", True),
            "transaction_events.enabled": test.pop("transaction_events_enabled", True),
            "distributed_tracing.sampler._root": test.pop("root", "adaptive"),
            "distributed_tracing.sampler._remote_parent_sampled": test.pop("remote_parent_sampled", "adaptive"),
            "distributed_tracing.sampler._remote_parent_not_sampled": test.pop("remote_parent_not_sampled", "adaptive"),
            "trusted_account_key": test.pop("trusted_account_key", None),
            "account_id": test.pop("account_id", None),
            "distributed_tracing.sampler.partial_granularity.enabled": test.pop("partial_granularity_enabled", False),
            "distributed_tracing.sampler.partial_granularity._root": test.pop("partial_granularity_root", "adaptive"),
            "distributed_tracing.sampler.partial_granularity._remote_parent_sampled": test.pop("partial_granularity_remote_parent_sampled", "adaptive"),
            "distributed_tracing.sampler.partial_granularity._remote_parent_not_sampled": test.pop("partial_granularity_remote_parent_not_sampled", "adaptive"),
        }
        full_gran_ratio = test.pop("full_granularity_ratio", None)
        if full_gran_ratio is not None:
            if settings["distributed_tracing.sampler._root"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.root.trace_id_ratio_based.ratio"] = full_gran_ratio
            if settings["distributed_tracing.sampler._remote_parent_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.remote_parent_sampled.trace_id_ratio_based.ratio"] = full_gran_ratio
            if settings["distributed_tracing.sampler._remote_parent_not_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.remote_parent_not_sampled.trace_id_ratio_based.ratio"] = full_gran_ratio
        partial_gran_ratio = test.pop("partial_granularity_ratio", None)
        if partial_gran_ratio is not None:
            if settings["distributed_tracing.sampler.partial_granularity._root"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.ratio"] = partial_gran_ratio
            if settings["distributed_tracing.sampler.partial_granularity._remote_parent_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.ratio"] = partial_gran_ratio
            if settings["distributed_tracing.sampler.partial_granularity._remote_parent_not_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.ratio"] = partial_gran_ratio

        force_adaptive_sampled = test.pop("force_adaptive_sampled", None)
        expected_metrics = test.pop("expected_metrics", [])
        raises_exception = test.pop("raises_exception", False)
        web_transaction = test.pop("web_transaction", False)
        inbound_headers = (test.pop("inbound_headers", None) or [{}])[0]
        expected_priority_between = test.pop("expected_priority_between", None)
        intrinsics = test.pop("intrinsics", {})
        common_exact_intrinsics = intrinsics.get("common", {}).get("exact", {})
        common_expected_intrinsics = intrinsics.get("common", {}).get("expected", [])
        common_unexpected_intrinsics = intrinsics.get("common", {}).get("unexpected", [])
        span_exact_intrinsics = intrinsics.get("Span", {}).get("exact", {})
        span_expected_intrinsics = intrinsics.get("Span", {}).get("expected", [])
        span_unexpected_intrinsics = intrinsics.get("Span", {}).get("unexpected", [])
        transaction_exact_intrinsics = intrinsics.get("Transaction", {}).get("exact", {})
        transaction_expected_intrinsics = intrinsics.get("Transaction", {}).get("expected", [])
        transaction_unexpected_intrinsics = intrinsics.get("Transaction", {}).get("unexpected", [])
        if "Transaction" in intrinsics.get("target_events", []):
            transaction_exact_intrinsics.update(common_exact_intrinsics)
            transaction_expected_intrinsics.extend(common_expected_intrinsics)
            transaction_unexpected_intrinsics.extend(common_unexpected_intrinsics)
        check_span_events = False
        if "Span" in intrinsics.get("target_events", []):
            check_span_events = True
            span_exact_intrinsics.update(common_exact_intrinsics)
            span_expected_intrinsics.extend(common_expected_intrinsics)
            span_unexpected_intrinsics.extend(common_unexpected_intrinsics)

        payload = (test.pop("outbound_payloads", None) or [{}])[0]
        traceparent_key_map = {"trace_id": "tr", "parent_id": "id", "version": "v", "trace_flags": "sa"}
        tracestate_key_map = {
          "tenant_id": "ac",
          "version": "v",
          "parent_type": "ty",
          "parent_account_id": "ac",
          "sampled": "sa",
          "priority": "pr",
          "parent_id": "pi",
          "timestamp": "ti",
          "parent_application_id": "ap",
          "span_id": "id",
          "transaction_id": "tx",
        }
        expected_traceparent_exact = {traceparent_key_map[key.split(".")[1]]: value for key, value in payload.get("exact", {}).items() if "traceparent" in key}
        expected_tracestate_exact = {tracestate_key_map[key.split(".")[1]]: value for key, value in payload.get("exact", {}).items() if "tracestate" in key}
        expected_traceparent = [traceparent_key_map[key.split(".")[1]] for key in payload.get("expected", []) if "traceparent" in key]
        expected_tracestate = [tracestate_key_map[key.split(".")[1]] for key in payload.get("expected", []) if "tracestate" in key]
        outbound_payloads = (
            expected_traceparent_exact,
            expected_tracestate_exact,
            expected_traceparent,
            expected_tracestate,
        )

        transport_type = test.pop("transport_type", "HTTP")

        assert not test, f"{test} has not been fully parsed"

        param = pytest.param(
            settings,
            force_adaptive_sampled,
            transport_type,
            raises_exception,
            web_transaction,
            inbound_headers,
            expected_priority_between,
            common_exact_intrinsics,
            common_expected_intrinsics,
            common_unexpected_intrinsics,
            transaction_exact_intrinsics,
            transaction_expected_intrinsics,
            transaction_unexpected_intrinsics,
            check_span_events,
            span_exact_intrinsics,
            span_expected_intrinsics,
            span_unexpected_intrinsics,
            outbound_payloads,
            expected_metrics,
            id=_id
        )
        result.append(param)

    return result


def override_compute_sampled(override):
    @transient_function_wrapper("newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled")
    def _override_compute_sampled(wrapped, instance, args, kwargs):
        sampled = wrapped(*args, **kwargs)
        if override is None:
            return sampled
        return override

    return _override_compute_sampled


@pytest.fixture
def create_transaction():
    def _create_transaction(test_name, web_transaction, transport_type, raises_exception, inbound_headers, outbound_payloads, expected_priority_between):

        def _task():
            txn = current_transaction()
            application = txn._application._agent._applications.get(txn.settings.app_name)
            # Re-initialize sampler proxy after overriding settings.
            application.sampler.__init__(txn.settings)

            if raises_exception:
                try:
                    1 / 0  # noqa: B018
                except ZeroDivisionError:
                    txn.notice_error()

            txn.accept_distributed_trace_headers(inbound_headers, transport_type)

            if outbound_payloads:
                headers = []
                txn.insert_distributed_trace_headers(headers)
                if test_name == "multiple_create_calls":
                    txn.insert_distributed_trace_headers(headers)
                headers = dict(headers)

                expected_traceparent_exact, expected_tracestate_exact, expected_traceparent, expected_tracestate = outbound_payloads

                if expected_traceparent_exact or expected_traceparent:
                    traceparent = W3CTraceParent.decode(headers["traceparent"])
                    for key, value in expected_traceparent_exact.items():
                        if key == "sa":
                            assert traceparent.get(key, None) == bool(int(value, 2))
                            continue
                        assert traceparent.get(key, None) == value
                    for key in expected_traceparent:
                        assert key in traceparent

                if expected_tracestate_exact or expected_tracestate:
                    vendors = W3CTraceState.decode(headers["tracestate"])
                    trusted_account_key = txn.settings.trusted_account_key
                    newrelic = vendors.pop(f"{trusted_account_key}@nr", "")
                    tracestate = NrTraceState.decode(newrelic, trusted_account_key)
                    for key, value in expected_tracestate_exact.items():
                        if key == "v":
                            assert tracestate.get(key, None) == value
                            continue
                        if key == "ty":
                            assert tracestate.get(key, None) == PARENT_TYPE[str(value)]
                            continue
                        if key == "sa":
                            assert tracestate.get(key, None) == bool(int(value))
                            continue
                        if key == "pr":
                            assert f"{tracestate.get(key, None):.6f}".rstrip("0") == value
                            continue
                        assert tracestate.get(key, None) == value
                    for key in expected_tracestate:
                        assert key in tracestate

                    if expected_priority_between:
                        assert expected_priority_between[0] < tracestate[key] < expected_priority_between[1]

        if web_transaction:
            request = newrelic.agent.WebTransactionWrapper(_task, name=test_name)
        else:
            request = newrelic.agent.BackgroundTaskWrapper(_task, name=test_name)

        return request

    return _create_transaction


@pytest.mark.parametrize(
    "settings,force_adaptive_sampled,transport_type,raises_exception,web_transaction,inbound_headers,expected_priority_between,exact_intrinsics,expected_intrinsics,unexpected_intrinsics,transaction_exact_intrinsics,transaction_expected_intrinsics,transaction_unexpected_intrinsics,check_span_events,span_exact_intrinsics,span_expected_intrinsics,span_unexpected_intrinsics,outbound_payloads,expected_metrics",
    load_tests(),
)
def test_distributed_tracing(
    settings,
    force_adaptive_sampled,
    transport_type,
    raises_exception,
    web_transaction,
    inbound_headers,
    expected_priority_between,
    exact_intrinsics,
    expected_intrinsics,
    unexpected_intrinsics,
    transaction_exact_intrinsics,
    transaction_expected_intrinsics,
    transaction_unexpected_intrinsics,
    check_span_events,
    span_exact_intrinsics,
    span_expected_intrinsics,
    span_unexpected_intrinsics,
    outbound_payloads,
    expected_metrics,
    request,
    create_transaction,
):
    test_name = request.node.callspec.id
    txn_event_required = {"agent": [], "user": [], "intrinsic": transaction_expected_intrinsics}
    txn_event_forgone = {"agent": [], "user": [], "intrinsic": transaction_unexpected_intrinsics}
    txn_event_exact = {"agent": {}, "user": {}, "intrinsic": transaction_exact_intrinsics}

    @validate_transaction_metrics(test_name, rollup_metrics=expected_metrics, background_task=not web_transaction)
    @validate_transaction_event_attributes(txn_event_required, txn_event_forgone, txn_event_exact)
    @override_compute_sampled(force_adaptive_sampled)
    @override_application_settings(settings)
    def _test():
        transaction = create_transaction(test_name, web_transaction, transport_type, raises_exception, inbound_headers, outbound_payloads, expected_priority_between)

        transaction()

    if raises_exception:
        error_event_required = {"agent": [], "user": [], "intrinsic": expected_intrinsics}
        error_event_forgone = {"agent": [], "user": [], "intrinsic": unexpected_intrinsics}
        error_event_exact = {"agent": {}, "user": {}, "intrinsic": exact_intrinsics}
        _test = validate_error_event_attributes(error_event_required, error_event_forgone, error_event_exact)(_test)

    if settings["span_events.enabled"]:
        if check_span_events:
            _test = validate_span_events(
                exact_intrinsics=span_exact_intrinsics, expected_intrinsics=span_expected_intrinsics, unexpected_intrinsics=span_unexpected_intrinsics
            )(_test)
    else:
        _test = validate_span_events(count=0)(_test)

    _test()
