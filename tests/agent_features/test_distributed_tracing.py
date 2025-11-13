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

import asyncio
import copy
import json
import time

import pytest
import webtest
from testing_support.fixtures import override_application_settings, validate_attributes, validate_attributes_complete
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_function_called import validate_function_called
from testing_support.validators.validate_function_not_called import validate_function_not_called
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.function_trace import function_trace
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper

try:
    from newrelic.core.infinite_tracing_pb2 import AttributeValue, Span
except:
    AttributeValue = None
    Span = None

from testing_support.mock_external_http_server import MockExternalHTTPHResponseHeadersServer
from testing_support.validators.validate_span_events import check_value_equals, validate_span_events

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask, background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import (
    accept_distributed_trace_headers,
    current_span_id,
    current_trace_id,
    current_transaction,
    insert_distributed_trace_headers,
)
from newrelic.api.web_transaction import WSGIWebTransaction
from newrelic.api.wsgi_application import wsgi_application
from newrelic.core.attribute import Attribute

# ruff: noqa: UP031
distributed_trace_intrinsics = ["guid", "traceId", "priority", "sampled"]
inbound_payload_intrinsics = [
    "parent.type",
    "parent.app",
    "parent.account",
    "parent.transportType",
    "parent.transportDuration",
]

payload = {
    "v": [0, 1],
    "d": {
        "ac": "1",
        "ap": "2827902",
        "id": "7d3efb1b173fecfa",
        "pa": "5e5733a911cfbc73",
        "pr": 10.001,
        "sa": True,
        "ti": 1518469636035,
        "tr": "d6b4ba0c3a712ca",
        "ty": "App",
    },
}
parent_order = ["parent_type", "parent_account", "parent_app", "parent_transport_type"]
parent_info = {
    "parent_type": payload["d"]["ty"],
    "parent_account": payload["d"]["ac"],
    "parent_app": payload["d"]["ap"],
    "parent_transport_type": "HTTP",
}


def validate_compact_span_event(
    name, compressed_span_count, expected_nr_durations_low_bound, expected_nr_durations_high_bound
):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        record_transaction_called = []
        recorded_span_events = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def capture_span_events(wrapped, instance, args, kwargs):
            events = []

            @transient_function_wrapper("newrelic.common.streaming_utils", "StreamBuffer.put")
            def stream_capture(wrapped, instance, args, kwargs):
                event = args[0]
                events.append(event)
                return wrapped(*args, **kwargs)

            record_transaction_called.append(True)
            try:
                result = stream_capture(wrapped)(*args, **kwargs)
            except:
                raise
            else:
                if not instance.settings.infinite_tracing.enabled:
                    events = [event for priority, seen_at, event in instance.span_events.pq]

                recorded_span_events.append(events)

            return result

        _new_wrapper = capture_span_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        captured_events = recorded_span_events.pop(-1)

        mismatches = []
        matching_span_events = 0

        def _span_details():
            details = [
                f"matching_span_events={matching_span_events}",
                f"mismatches={mismatches}",
                f"captured_events={captured_events}",
            ]
            return "\n".join(details)

        for captured_event in captured_events:
            if Span and isinstance(captured_event, Span):
                intrinsics = captured_event.intrinsics
                user_attrs = captured_event.user_attributes
                agent_attrs = captured_event.agent_attributes
            else:
                intrinsics, _, agent_attrs = captured_event

            # Find the span by name.
            if not check_value_equals(intrinsics, "name", name):
                continue
            assert check_value_length(agent_attrs, "nr.ids", compressed_span_count - 1, mismatches), _span_details()
            assert check_value_between(
                agent_attrs,
                "nr.durations",
                expected_nr_durations_low_bound,
                expected_nr_durations_high_bound,
                mismatches,
            ), _span_details()
            matching_span_events += 1

        assert matching_span_events == 1, _span_details()
        return val

    return _validate_wrapper


def check_value_between(dictionary, key, expected_min, expected_max, mismatches):
    value = dictionary.get(key)
    if AttributeValue and isinstance(value, AttributeValue):
        for _, val in value.ListFields():
            if not (expected_min < val < expected_max):
                mismatches.append(f"key: {key}, not {expected_min} < {val} < {expected_max}")
                return False
        return True
    else:
        if not (expected_min < value < expected_max):
            mismatches.append(f"key: {key}, not {expected_min} < {value} < {expected_max}")
            return False
        return True


def check_value_length(dictionary, key, expected_length, mismatches):
    value = dictionary.get(key)
    if AttributeValue and isinstance(value, AttributeValue):
        for _, val in value.ListFields():
            if len(val) != expected_length:
                mismatches.append(f"key: {key}, not len({val}) == {expected_length}")
                return False
        return True
    else:
        if len(value) != expected_length:
            mismatches.append(f"key: {key}, not len({value}) == {expected_length}")
            return False
        return True


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = "200 OK"
    output = b"hello world"
    response_headers = [("Content-type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]

    txn = current_transaction()

    # Make assertions on the WSGIWebTransaction object
    assert txn._distributed_trace_state
    assert txn.parent_type == "App"
    assert txn.parent_app == "2827902"
    assert txn.parent_account == "1"
    assert txn.parent_span == "7d3efb1b173fecfa"
    assert txn.parent_transport_type == "HTTP"
    assert isinstance(txn.parent_transport_duration, float)
    assert txn._trace_id == "d6b4ba0c3a712ca"
    assert txn.priority == 10.001
    assert txn.sampled

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)

_override_settings = {"trusted_account_key": "1", "distributed_tracing.enabled": True}


_metrics = [
    ("Supportability/DistributedTrace/AcceptPayload/Success", 1),
    ("Supportability/TraceContext/Accept/Success", None),
]


@override_application_settings(_override_settings)
@validate_transaction_metrics("", group="Uri", rollup_metrics=_metrics)
def test_distributed_tracing_web_transaction():
    headers = {"newrelic": json.dumps(payload)}
    response = test_application.get("/", headers=headers)
    assert "X-NewRelic-App-Data" not in response.headers


@pytest.mark.parametrize("span_events", (True, False))
@pytest.mark.parametrize("accept_payload", (True, False))
def test_distributed_trace_attributes(span_events, accept_payload):
    if accept_payload:
        _required_intrinsics = distributed_trace_intrinsics + inbound_payload_intrinsics
        _forgone_txn_intrinsics = []
        _forgone_error_intrinsics = []
        _exact_intrinsics = {
            "parent.type": "Mobile",
            "parent.app": "2827902",
            "parent.account": "1",
            "parent.transportType": "HTTP",
            "traceId": "d6b4ba0c3a712ca",
        }
        _exact_txn_attributes = {"agent": {}, "user": {}, "intrinsic": _exact_intrinsics.copy()}
        _exact_error_attributes = {"agent": {}, "user": {}, "intrinsic": _exact_intrinsics.copy()}
        _exact_txn_attributes["intrinsic"]["parentId"] = "7d3efb1b173fecfa"
        _exact_txn_attributes["intrinsic"]["parentSpanId"] = "c86df80de2e6f51c"

        _forgone_error_intrinsics.append("parentId")
        _forgone_error_intrinsics.append("parentSpanId")
        _forgone_txn_intrinsics.append("grandparentId")
        _forgone_error_intrinsics.append("grandparentId")

        _required_attributes = {"intrinsic": _required_intrinsics, "agent": [], "user": []}
        _forgone_txn_attributes = {"intrinsic": _forgone_txn_intrinsics, "agent": [], "user": []}
        _forgone_error_attributes = {"intrinsic": _forgone_error_intrinsics, "agent": [], "user": []}
    else:
        _required_intrinsics = distributed_trace_intrinsics
        _forgone_txn_intrinsics = _forgone_error_intrinsics = [
            *inbound_payload_intrinsics,
            "grandparentId",
            "parentId",
            "parentSpanId",
        ]

        _required_attributes = {"intrinsic": _required_intrinsics, "agent": [], "user": []}
        _forgone_txn_attributes = {"intrinsic": _forgone_txn_intrinsics, "agent": [], "user": []}
        _forgone_error_attributes = {"intrinsic": _forgone_error_intrinsics, "agent": [], "user": []}
        _exact_txn_attributes = _exact_error_attributes = None

    _forgone_trace_intrinsics = _forgone_error_intrinsics

    test_settings = _override_settings.copy()
    test_settings["span_events.enabled"] = span_events

    @override_application_settings(test_settings)
    @validate_transaction_event_attributes(_required_attributes, _forgone_txn_attributes, _exact_txn_attributes)
    @validate_error_event_attributes(_required_attributes, _forgone_error_attributes, _exact_error_attributes)
    @validate_attributes("intrinsic", _required_intrinsics, _forgone_trace_intrinsics)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        txn = current_transaction()

        payload = {
            "v": [0, 1],
            "d": {
                "ty": "Mobile",
                "ac": "1",
                "ap": "2827902",
                "id": "c86df80de2e6f51c",
                "tr": "d6b4ba0c3a712ca",
                "ti": 1518469636035,
                "tx": "7d3efb1b173fecfa",
            },
        }
        payload["d"]["pa"] = "5e5733a911cfbc73"

        if accept_payload:
            headers = {"newrelic": payload}
            result = accept_distributed_trace_headers(headers)
            assert result
        else:
            headers = []
            insert_distributed_trace_headers(headers)
            assert headers

        try:
            raise ValueError("cookies")
        except ValueError:
            txn.notice_error()

    _test()


_forgone_attributes = {"agent": [], "user": [], "intrinsic": ([*inbound_payload_intrinsics, "grandparentId"])}


@override_application_settings(_override_settings)
@validate_transaction_event_attributes({}, _forgone_attributes)
@validate_error_event_attributes({}, _forgone_attributes)
@validate_attributes("intrinsic", {}, _forgone_attributes["intrinsic"])
@background_task(name="test_distributed_trace_attrs_omitted")
def test_distributed_trace_attrs_omitted():
    txn = current_transaction()
    try:
        raise ValueError("cookies")
    except ValueError:
        txn.notice_error()


# test our distributed_trace metrics by creating a transaction and then forcing
# it to process a distributed trace payload
@pytest.mark.parametrize("web_transaction", (True, False))
@pytest.mark.parametrize("gen_error", (True, False))
@pytest.mark.parametrize("has_parent", (True, False))
def test_distributed_tracing_metrics(web_transaction, gen_error, has_parent):
    def _make_dt_tag(pi):
        return "{}/{}/{}/{}/all".format(*tuple(pi[x] for x in parent_order))

    # figure out which metrics we'll see based on the test params
    # note: we'll always see DurationByCaller if the distributed
    # tracing flag is turned on
    metrics = ["DurationByCaller"]
    if gen_error:
        metrics.append("ErrorsByCaller")
    if has_parent:
        metrics.append("TransportDuration")

    tag = None
    dt_payload = copy.deepcopy(payload)

    # if has_parent is True, our metric name will be info about the parent,
    # otherwise it is Unknown/Unknown/Unknown/Unknown
    if has_parent:
        tag = _make_dt_tag(parent_info)
    else:
        # tag = _make_dt_tag(dict((x, "Unknown") for x in parent_order))
        tag = _make_dt_tag(dict.fromkeys(parent_info.keys(), "Unknown"))
        del dt_payload["d"]["tr"]

    # now run the test
    transaction_name = f"test_dt_metrics_{'_'.join(metrics)}"
    _rollup_metrics = [(f"{x}/{tag}{bt}", 1) for x in metrics for bt in ["", "Web" if web_transaction else "Other"]]

    def _make_test_transaction():
        application = application_instance()

        if not web_transaction:
            return BackgroundTask(application, transaction_name)

        environ = {"REQUEST_URI": "/trace_ends_after_txn"}
        tn = WSGIWebTransaction(application, environ)
        tn.set_transaction_name(transaction_name)
        return tn

    @override_application_settings(_override_settings)
    @validate_transaction_metrics(
        transaction_name, background_task=not (web_transaction), rollup_metrics=_rollup_metrics
    )
    def _test():
        with _make_test_transaction() as transaction:
            dt_headers = {"newrelic": dt_payload}
            transaction.accept_distributed_trace_headers(dt_headers)

            if gen_error:
                try:
                    1 / 0  # noqa: B018
                except ZeroDivisionError:
                    transaction.notice_error()

    _test()


NEW_RELIC_ACCEPTED = [
    ("Supportability/DistributedTrace/AcceptPayload/Success", 1),
    ("Supportability/TraceContext/Accept/Success", None),
    ("Supportability/TraceContext/TraceParent/Accept/Success", None),
    ("Supportability/TraceContext/Accept/Success", None),
]
TRACE_CONTEXT_ACCEPTED = [
    ("Supportability/TraceContext/Accept/Success", 1),
    ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
    ("Supportability/TraceContext/Accept/Success", 1),
    ("Supportability/DistributedTrace/AcceptPayload/Success", None),
]
NO_HEADERS_ACCEPTED = [
    ("Supportability/DistributedTrace/AcceptPayload/Success", None),
    ("Supportability/TraceContext/Accept/Success", None),
    ("Supportability/TraceContext/TraceParent/Accept/Success", None),
    ("Supportability/TraceContext/Accept/Success", None),
]
TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"
TRACESTATE = "rojo=f06a0ba902b7,congo=t61rcWkgMzE"


@pytest.mark.parametrize(
    "traceparent,tracestate,newrelic,metrics",
    [
        (False, False, False, NO_HEADERS_ACCEPTED),
        (False, False, True, NEW_RELIC_ACCEPTED),
        (False, True, True, NEW_RELIC_ACCEPTED),
        (False, True, False, NO_HEADERS_ACCEPTED),
        (True, True, True, TRACE_CONTEXT_ACCEPTED),
        (True, False, False, TRACE_CONTEXT_ACCEPTED),
        (True, False, True, TRACE_CONTEXT_ACCEPTED),
        (True, True, False, TRACE_CONTEXT_ACCEPTED),
    ],
)
@override_application_settings(_override_settings)
def test_distributed_tracing_backwards_compatibility(traceparent, tracestate, newrelic, metrics):
    headers = []
    if traceparent:
        headers.append(("traceparent", TRACEPARENT))
    if tracestate:
        headers.append(("tracestate", TRACESTATE))
    if newrelic:
        headers.append(("newrelic", json.dumps(payload)))

    @validate_transaction_metrics(
        "test_distributed_tracing_backwards_compatibility", background_task=True, rollup_metrics=metrics
    )
    @background_task(name="test_distributed_tracing_backwards_compatibility")
    def _test():
        accept_distributed_trace_headers(headers)

    _test()


@background_task(name="test_current_trace_id_api_inside_transaction")
def test_current_trace_id_api_inside_transaction():
    trace_id = current_trace_id()
    assert len(trace_id) == 32
    assert trace_id == current_transaction().trace_id


def test_current_trace_id_api_outside_transaction():
    trace_id = current_trace_id()
    assert trace_id is None


@background_task(name="test_current_span_id_api_inside_transaction")
def test_current_span_id_inside_transaction():
    span_id = current_span_id()
    assert span_id == current_trace().guid


def test_current_span_id_outside_transaction():
    span_id = current_span_id()
    assert span_id is None


@pytest.mark.parametrize("trusted_account_key", ("1", None), ids=("tk_set", "tk_unset"))
def test_outbound_dt_payload_generation(trusted_account_key):
    @override_application_settings(
        {
            "distributed_tracing.enabled": True,
            "account_id": "1",
            "trusted_account_key": trusted_account_key,
            "primary_application_id": "1",
        }
    )
    @background_task(name="test_outbound_dt_payload_generation")
    def _test_outbound_dt_payload_generation():
        transaction = current_transaction()
        payload = ExternalTrace.generate_request_headers(transaction)
        if trusted_account_key:
            assert payload
            # Ensure trusted account key present as vendor
            assert dict(payload)["tracestate"].startswith("1@nr=")
        else:
            assert not payload

    _test_outbound_dt_payload_generation()


@pytest.mark.parametrize("trusted_account_key", ("1", None), ids=("tk_set", "tk_unset"))
def test_inbound_dt_payload_acceptance(trusted_account_key):
    @override_application_settings(
        {
            "distributed_tracing.enabled": True,
            "account_id": "1",
            "trusted_account_key": trusted_account_key,
            "primary_application_id": "1",
        }
    )
    @background_task(name="_test_inbound_dt_payload_acceptance")
    def _test_inbound_dt_payload_acceptance():
        transaction = current_transaction()

        payload = {
            "v": [0, 1],
            "d": {
                "ty": "Mobile",
                "ac": "1",
                "tk": "1",
                "ap": "2827902",
                "pa": "5e5733a911cfbc73",
                "id": "7d3efb1b173fecfa",
                "tr": "d6b4ba0c3a712ca",
                "ti": 1518469636035,
                "tx": "8703ff3d88eefe9d",
            },
        }
        headers = {"newrelic": payload}
        result = transaction.accept_distributed_trace_headers(headers)
        if trusted_account_key:
            assert result
        else:
            assert not result

    _test_inbound_dt_payload_acceptance()


@pytest.mark.parametrize(
    "traceparent_sampled,newrelic_sampled,remote_parent_sampled_setting,remote_parent_not_sampled_setting,expected_sampled,expected_priority,expected_adaptive_sampling_algo_called",
    (
        (True, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "always_on", "default", True, 2, False),  # Always sampled.
        (True, None, "always_off", "default", False, 0, False),  # Never sampled.
        (False, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
        (False, None, "always_on", "default", None, None, True),  # Uses adaptive sampling alog.
        (False, None, "always_off", "default", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "default", "always_on", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "default", "always_off", None, None, True),  # Uses adaptive sampling algo.
        (False, None, "default", "always_on", True, 2, False),  # Always sampled.
        (False, None, "default", "always_off", False, 0, False),  # Never sampled.
        (True, True, "default", "default", True, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (True, False, "default", "default", False, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (False, False, "default", "default", False, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (True, False, "always_on", "default", True, 2, False),  # Always sampled.
        (True, True, "always_off", "default", False, 0, False),  # Never sampled.
        (False, False, "default", "always_on", True, 2, False),  # Always sampled.
        (False, True, "default", "always_off", False, 0, False),  # Never sampled.
        (None, True, "default", "default", True, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, True, "always_on", "default", True, 2, False),  # Always sampled.
        (None, True, "always_off", "default", False, 0, False),  # Never sampled.
        (None, False, "default", "default", False, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, False, "always_on", "default", False, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, True, "default", "always_on", True, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, False, "default", "always_on", True, 2, False),  # Always sampled.
        (None, False, "default", "always_off", False, 0, False),  # Never sampled.
        (None, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
    ),
)
def test_distributed_trace_remote_parent_sampling_decision_full_granularity(
    traceparent_sampled,
    newrelic_sampled,
    remote_parent_sampled_setting,
    remote_parent_not_sampled_setting,
    expected_sampled,
    expected_priority,
    expected_adaptive_sampling_algo_called,
):
    required_intrinsics = []
    if expected_sampled is not None:
        required_intrinsics.append(Attribute(name="sampled", value=expected_sampled, destinations=0b110))
    if expected_priority is not None:
        required_intrinsics.append(Attribute(name="priority", value=expected_priority, destinations=0b110))

    test_settings = _override_settings.copy()
    test_settings.update(
        {
            "distributed_tracing.sampler.full_granularity.remote_parent_sampled": remote_parent_sampled_setting,
            "distributed_tracing.sampler.full_granularity.remote_parent_not_sampled": remote_parent_not_sampled_setting,
            "span_events.enabled": True,
        }
    )
    if expected_adaptive_sampling_algo_called:
        function_called_decorator = validate_function_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )
    else:
        function_called_decorator = validate_function_not_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )

    @function_called_decorator
    @override_application_settings(test_settings)
    @validate_attributes_complete("intrinsic", required_intrinsics)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        txn = current_transaction()

        if traceparent_sampled is not None:
            headers = {
                "traceparent": f"00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-{int(traceparent_sampled):02x}",
                "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":true,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
            }
            if newrelic_sampled is not None:
                headers["tracestate"] = (
                    f"1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-{int(newrelic_sampled)}-1.23456-1518469636035"
                )
        else:
            headers = {
                "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"1","ap":"51424","id":"00f067aa0ba902b7","tr":"0af7651916cd43dd8448eb211c80319c","pr":0.1234,"sa":%s,"ti":1482959525577,"tx":"0af7651916cd43dd"}}'
                % (str(newrelic_sampled).lower())
            }
        accept_distributed_trace_headers(headers)

    _test()


@pytest.mark.parametrize(
    "traceparent_sampled,newrelic_sampled,remote_parent_sampled_setting,remote_parent_not_sampled_setting,expected_sampled,expected_priority,expected_adaptive_sampling_algo_called",
    (
        (True, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "always_on", "default", True, 2, False),  # Always sampled.
        (True, None, "always_off", "default", False, 0, False),  # Never sampled.
        (False, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
        (False, None, "always_on", "default", None, None, True),  # Uses adaptive sampling alog.
        (False, None, "always_off", "default", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "default", "always_on", None, None, True),  # Uses adaptive sampling algo.
        (True, None, "default", "always_off", None, None, True),  # Uses adaptive sampling algo.
        (False, None, "default", "always_on", True, 2, False),  # Always sampled.
        (False, None, "default", "always_off", False, 0, False),  # Never sampled.
        (True, True, "default", "default", True, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (True, False, "default", "default", False, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (False, False, "default", "default", False, 1.23456, False),  # Uses sampling decision in W3C TraceState header.
        (True, False, "always_on", "default", True, 2, False),  # Always sampled.
        (True, True, "always_off", "default", False, 0, False),  # Never sampled.
        (False, False, "default", "always_on", True, 2, False),  # Always sampled.
        (False, True, "default", "always_off", False, 0, False),  # Never sampled.
        (None, True, "default", "default", True, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, True, "always_on", "default", True, 2, False),  # Always sampled.
        (None, True, "always_off", "default", False, 0, False),  # Never sampled.
        (None, False, "default", "default", False, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, False, "always_on", "default", False, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, True, "default", "always_on", True, 0.1234, False),  # Uses sampling and priority from newrelic header.
        (None, False, "default", "always_on", True, 2, False),  # Always sampled.
        (None, False, "default", "always_off", False, 0, False),  # Never sampled.
        (None, None, "default", "default", None, None, True),  # Uses adaptive sampling algo.
    ),
)
def test_distributed_trace_remote_parent_sampling_decision_partial_granularity(
    traceparent_sampled,
    newrelic_sampled,
    remote_parent_sampled_setting,
    remote_parent_not_sampled_setting,
    expected_sampled,
    expected_priority,
    expected_adaptive_sampling_algo_called,
):
    required_intrinsics = []
    if expected_sampled is not None:
        required_intrinsics.append(Attribute(name="sampled", value=expected_sampled, destinations=0b110))
    if expected_priority is not None:
        required_intrinsics.append(Attribute(name="priority", value=expected_priority, destinations=0b110))

    test_settings = _override_settings.copy()
    test_settings.update(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": remote_parent_sampled_setting,
            "distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled": remote_parent_not_sampled_setting,
            "span_events.enabled": True,
        }
    )
    if expected_adaptive_sampling_algo_called:
        function_called_decorator = validate_function_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )
    else:
        function_called_decorator = validate_function_not_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )

    @function_called_decorator
    @override_application_settings(test_settings)
    @validate_attributes_complete("intrinsic", required_intrinsics)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        txn = current_transaction()

        if traceparent_sampled is not None:
            headers = {
                "traceparent": f"00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-{int(traceparent_sampled):02x}",
                "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":true,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
            }
            if newrelic_sampled is not None:
                headers["tracestate"] = (
                    f"1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-{int(newrelic_sampled)}-1.23456-1518469636035"
                )
        else:
            headers = {
                "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"1","ap":"51424","id":"00f067aa0ba902b7","tr":"0af7651916cd43dd8448eb211c80319c","pr":0.1234,"sa":%s,"ti":1482959525577,"tx":"0af7651916cd43dd"}}'
                % (str(newrelic_sampled).lower())
            }
        accept_distributed_trace_headers(headers)

    _test()


@pytest.mark.parametrize(
    "full_granularity_enabled,full_granularity_remote_parent_sampled_setting,partial_granularity_enabled,partial_granularity_remote_parent_sampled_setting,expected_sampled,expected_priority,expected_adaptive_sampling_algo_called",
    (
        (True, "always_off", True, "adaptive", None, None, True),  # Uses adaptive sampling algo.
        (True, "always_on", True, "adaptive", True, 2, False),  # Uses adaptive sampling algo.
        (False, "always_on", False, "adaptive", False, 0, False),  # Uses adaptive sampling algo.
    ),
)
def test_distributed_trace_remote_parent_sampling_decision_between_full_and_partial_granularity(
    full_granularity_enabled,
    full_granularity_remote_parent_sampled_setting,
    partial_granularity_enabled,
    partial_granularity_remote_parent_sampled_setting,
    expected_sampled,
    expected_priority,
    expected_adaptive_sampling_algo_called,
):
    required_intrinsics = []
    if expected_sampled is not None:
        required_intrinsics.append(Attribute(name="sampled", value=expected_sampled, destinations=0b110))
    if expected_priority is not None:
        required_intrinsics.append(Attribute(name="priority", value=expected_priority, destinations=0b110))

    test_settings = _override_settings.copy()
    test_settings.update(
        {
            "distributed_tracing.sampler.full_granularity.enabled": full_granularity_enabled,
            "distributed_tracing.sampler.partial_granularity.enabled": partial_granularity_enabled,
            "distributed_tracing.sampler.full_granularity.remote_parent_sampled": full_granularity_remote_parent_sampled_setting,
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": partial_granularity_remote_parent_sampled_setting,
            "span_events.enabled": True,
        }
    )
    if expected_adaptive_sampling_algo_called:
        function_called_decorator = validate_function_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )
    else:
        function_called_decorator = validate_function_not_called(
            "newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled"
        )

    @function_called_decorator
    @override_application_settings(test_settings)
    @validate_attributes_complete("intrinsic", required_intrinsics)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)

    _test()


def test_partial_granularity_max_compressed_spans():
    """
    Tests `nr.ids` does not exceed 1024 byte limit.
    """

    async def test(index):
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            time.sleep(0.1)

    @function_trace()
    async def call_tests():
        tasks = [test(i) for i in range(65)]
        await asyncio.gather(*tasks)

    @validate_span_events(
        count=1,  # Entry span.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_max_compressed_spans.<locals>._test"
        },
        expected_intrinsics=["duration", "timestamp"],
    )
    @validate_span_events(
        count=1,  # 1 external compressed span.
        exact_intrinsics={"name": "External/localhost:3000/requests/GET"},
        exact_agents={"http.url": "http://localhost:3000/"},
        expected_agents=["nr.durations", "nr.ids"],
    )
    @validate_compact_span_event(
        name="External/localhost:3000/requests/GET",
        # `nr.ids` can only hold 63 ids but duration reflects all compressed spans.
        compressed_span_count=64,
        expected_nr_durations_low_bound=6.5,
        expected_nr_durations_high_bound=6.8,  # 64 of these adds > .2 overhead.
    )
    @background_task()
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)
        asyncio.run(call_tests())

    _test = override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": "compact",
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )(_test)

    _test()


def test_partial_granularity_compressed_span_attributes_in_series():
    """
    Tests compressed span attributes when compressed span times are serial.
    Aka: each span ends before the next compressed span begins.
    """

    async def test(index):
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            time.sleep(0.1)

    @function_trace()
    async def call_tests():
        tasks = [test(i) for i in range(3)]
        await asyncio.gather(*tasks)

    @validate_span_events(
        count=1,  # Entry span.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_compressed_span_attributes_in_series.<locals>._test"
        },
        expected_intrinsics=["duration", "timestamp"],
    )
    @validate_span_events(
        count=1,  # 1 external compressed span.
        exact_intrinsics={"name": "External/localhost:3000/requests/GET"},
        exact_agents={"http.url": "http://localhost:3000/"},
        expected_agents=["nr.durations", "nr.ids"],
    )
    @validate_compact_span_event(
        name="External/localhost:3000/requests/GET",
        compressed_span_count=3,
        expected_nr_durations_low_bound=0.3,
        expected_nr_durations_high_bound=0.4,
    )
    @background_task()
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)
        asyncio.run(call_tests())

    _test = override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": "compact",
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )(_test)

    _test()


def test_partial_granularity_compressed_span_attributes_overlapping():
    """
    Tests compressed span attributes when compressed span times overlap.
    Aka: the next span begins in the middle of the first span.
    """

    @validate_span_events(
        count=1,  # Entry span.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_compressed_span_attributes_overlapping.<locals>._test"
        },
        expected_intrinsics=["duration", "timestamp"],
    )
    @validate_span_events(
        count=1,  # 1 external compressed span.
        exact_intrinsics={"name": "External/localhost:3000/requests/GET"},
        exact_agents={"http.url": "http://localhost:3000/"},
        expected_agents=["nr.durations", "nr.ids"],
    )
    @validate_compact_span_event(
        name="External/localhost:3000/requests/GET",
        compressed_span_count=2,
        expected_nr_durations_low_bound=0.1,
        expected_nr_durations_high_bound=0.2,
    )
    @background_task()
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace1:
            # Override terminal_node so we can create a nested exit span.
            trace1.terminal_node = lambda: False
            trace2 = ExternalTrace("requests", "http://localhost:3000/", method="GET")
            trace2.__enter__()
            time.sleep(0.1)
        trace2.__exit__(None, None, None)

    _test = override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": "compact",
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )(_test)

    _test()


def test_partial_granularity_reduced_span_attributes():
    """
    In reduced mode, only inprocess spans are dropped.
    """

    @function_trace()
    def foo():
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            trace.add_custom_attribute("custom", "bar")

    @validate_span_events(
        count=1,  # Entry span.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_reduced_span_attributes.<locals>._test"
        },
        expected_intrinsics=["duration", "timestamp"],
        expected_agents=["code.function", "code.lineno", "code.namespace"],
    )
    @validate_span_events(
        count=0,  # Function foo span should not be present.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_reduced_span_attributes.<locals>.foo"
        },
        expected_intrinsics=["duration", "timestamp"],
    )
    @validate_span_events(
        count=2,  # 2 external spans.
        exact_intrinsics={"name": "External/localhost:3000/requests/GET"},
        exact_agents={"http.url": "http://localhost:3000/"},
        exact_users={"custom": "bar"},
    )
    @background_task()
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            # Override terminal_node so we can create a nested exit span.
            trace.terminal_node = lambda: False
            trace.add_custom_attribute("custom", "bar")
            foo()

    _test = override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": "reduced",
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )(_test)

    _test()


def test_partial_granularity_essential_span_attributes():
    """
    In essential mode, inprocess spans are dropped and non-entity synthesis attributes.
    """

    @function_trace()
    def foo():
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            trace.add_custom_attribute("custom", "bar")

    @validate_span_events(
        count=1,  # Entry span.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_essential_span_attributes.<locals>._test"
        },
        expected_intrinsics=["duration", "timestamp"],
        unexpected_agents=["code.function", "code.lineno", "code.namespace"],
    )
    @validate_span_events(
        count=0,  # Function foo span should not be present.
        exact_intrinsics={
            "name": "Function/test_distributed_tracing:test_partial_granularity_essential_span_attributes.<locals>.foo"
        },
        expected_intrinsics=["duration", "timestamp"],
    )
    @validate_span_events(
        count=2,  # 2 external spans.
        exact_intrinsics={"name": "External/localhost:3000/requests/GET"},
        exact_agents={"http.url": "http://localhost:3000/"},
        unexpected_users=["custom"],
    )
    @background_task()
    def _test():
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"}
        accept_distributed_trace_headers(headers)
        with ExternalTrace("requests", "http://localhost:3000/", method="GET") as trace:
            # Override terminal_node so we can create a nested exit span.
            trace.terminal_node = lambda: False
            trace.add_custom_attribute("custom", "bar")
            foo()

    _test = override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": "essential",
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )(_test)

    _test()
