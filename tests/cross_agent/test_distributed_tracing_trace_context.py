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
            "distributed_tracing.sampler.full_granularity.enabled": test.pop("full_granularity_enabled", False),
            "distributed_tracing.enabled": test.pop("distributed_tracing_enabled", True),
            "span_events.enabled": test.pop("span_events_enabled", True),
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
        if full_gran_ratio:
            if settings["distributed_tracing.sampler._root"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.root.trace_id_ratio_based.ratio"] = full_gran_ratio
            if settings["distributed_tracing.sampler._remote_parent_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.remote_parent_sampled.trace_id_ratio_based.ratio"] = full_gran_ratio
            if settings["distributed_tracing.sampler._remote_parent_not_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.remote_parent_not_sampled.trace_id_ratio_based.ratio"] = full_gran_ratio
        partial_gran_ratio = test.pop("partial_granularity_ratio", None)
        if partial_gran_ratio:
            if settings["distributed_tracing.sampler.partial_granularity._root"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.ratio"] = partial_gran_ratio
            if settings["distributed_tracing.sampler.partial_granularity._remote_parent_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.ratio"] = partial_gran_ratio
            if settings["distributed_tracing.sampler.partial_granularity._remote_parent_not_sampled"] == "trace_id_ratio_based":
                settings["distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.ratio"] = partial_gran_ratio

        force_adaptive_sampled = test.pop("force_adaptive_sampled", None)
        raises_exception = test.pop("raises_exception", False)
        web_transaction = test.pop("web_transaction", False)
        inbound_headers = test.pop("inbound_headers", [])
        expected_priority = test.pop("expected_priority_between", None)
        intrinsics = test.pop("intrinsics")
        exact_intrinsics = intrinsics["common"].get("exact", {})
        expected_intrinsics = intrinsics["common"].get("expected", [])
        unexpected_intrinsics = intrinsics["common"].get("unexpected", [])
        outbound_payloads = test.pop("outbound_payloads", [])
        transport_type = test.pop("transport_type", "HTTP")

        assert not test, f"{test} has not been fully parsed"

        param = pytest.param(
            {
                "settings": settings,
                "force_adaptive_sampled": force_adaptive_sampled,
                "raises_exception": raises_exception,
                "web_transaction": web_transaction,
                "inbound_headers": inbound_headers,
                "expected_priority": expected_priority,
                "exact_intrinsics": exact_intrinsics,
                "expected_intrinsics": expected_intrinsics,
                "unexpected_intrinsics": unexpected_intrinsics,
                "outbound_payloads": outbound_payloads,
            },
            id=test.get("test_name")
        )
        result.append(param)

    return result


def override_compute_sampled(override):
    @transient_function_wrapper("newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled")
    def _override_compute_sampled(wrapped, instance, args, kwargs):
        if override is None:
            return wrapped(*args, **kwargs)
        if override:
            return True
        else:
            return False

    return _override_compute_sampled


def assert_payload(payload, payload_assertions, major_version, minor_version):
    assert payload

    # flatten payload so it matches the test:
    #   payload['d']['ac'] -> payload['d.ac']
    d = payload.pop("d")
    for key, value in d.items():
        payload[f"d.{key}"] = value

    for expected in payload_assertions.get("expected", []):
        assert expected in payload

    for unexpected in payload_assertions.get("unexpected", []):
        assert unexpected not in payload

    for key, value in payload_assertions.get("exact", {}).items():
        assert key in payload
        if isinstance(value, list):
            value = tuple(value)
        assert payload[key] == value

    assert payload["v"][0] == major_version
    assert payload["v"][1] == minor_version


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = "200 OK"
    output = b"hello world"
    response_headers = [("Content-type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]

    txn = current_transaction()
    txn.set_transaction_name(test_settings["test_name"])

    if not test_settings["web_transaction"]:
        txn.background_task = True

    if test_settings["raises_exception"]:
        try:
            1 / 0  # noqa: B018
        except ZeroDivisionError:
            txn.notice_error()

    extra_inbound_payloads = test_settings["extra_inbound_payloads"]
    for payload, expected_result in extra_inbound_payloads:
        headers = {"newrelic": payload}
        result = txn.accept_distributed_trace_headers(headers, test_settings["transport_type"])
        assert result is expected_result

    outbound_payloads = test_settings["outbound_payloads"]
    if outbound_payloads:
        for payload_assertions in outbound_payloads:
            headers = []
            txn.insert_distributed_trace_headers(headers)
            # To revert to the dict format of the payload, use this:
            payload = json.loads(
                base64.b64decode([value for key, value in headers if key == "newrelic"][0]).decode("utf-8")
            )
            payload_version = payload.get("v")
            if payload_version and isinstance(payload_version, list):
                payload["v"] = tuple(payload_version)
            assert_payload(payload, payload_assertions, test_settings["major_version"], test_settings["minor_version"])

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)


@pytest.mark.parametrize(_parameters, load_tests())
def test_distributed_tracing(
    settings,
    force_adaptive_sampled,
    raises_exception,
    web_transaction,
    inbound_headers,
    expected_priority,
    exact_intrinsics,
    expected_intrinsics,
    unexpected_intrinsics,
    outbound_payloads,
):
    txn_event_required = {"agent": [], "user": [], "intrinsic": expected_intrinsics}
    txn_event_forgone = {"agent": [], "user": [], "intrinsic": unexpected_intrinsics}
    txn_event_exact = {"agent": {}, "user": {}, "intrinsic": exact_intrinsics}

    @validate_transaction_metrics(test_name, rollup_metrics=expected_metrics, background_task=not web_transaction)
    @validate_transaction_event_attributes(txn_event_required, txn_event_forgone, txn_event_exact)
    @override_compute_sampled(force_adaptive_sampled)
    @override_application_settings(settings)
    def _test():
        response = test_application.get("/", headers=inbound_headers)

    if raises_exception:
        error_event_required = {"agent": [], "user": [], "intrinsic": common_required}
        error_event_forgone = {"agent": [], "user": [], "intrinsic": common_forgone}
        error_event_exact = {"agent": {}, "user": {}, "intrinsic": common_exact}
        _test = validate_error_event_attributes(error_event_required, error_event_forgone, error_event_exact)(_test)

    _test()
