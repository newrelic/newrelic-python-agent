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

import pytest
from opentelemetry import propagate as otel_api_propagate
from opentelemetry import trace as otel_api_trace
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes

from newrelic.api.background_task import background_task
from newrelic.api.transaction import accept_distributed_trace_headers, current_transaction

PROPAGATOR = otel_api_propagate.get_global_textmap()

_override_settings = {"trusted_account_key": "1", "distributed_tracing.enabled": True, "span_events.enabled": True}


@pytest.mark.parametrize("telemetry", ["newrelic", "opentelemetry"])
@pytest.mark.parametrize("propagation", [accept_distributed_trace_headers, PROPAGATOR.extract])
def test_distributed_trace_header_compatibility_full_granularity(telemetry, propagation):
    """
    Args:
        telemetry (str): either "newrelic", or "opentelemetry"
            Denotes which propagation function was used to
            insert/inject the distributed trace headers.
            "newrelic" => `insert_distributed_trace_headers`
            "opentelemetry" => `PROPAGATOR.inject` from OpenTelemetry API
        propagation (func): The propagation function to use.
            Either `accept_distributed_trace_headers`
            or `PROPAGATOR.extract`.
    """

    @override_application_settings(_override_settings)
    @validate_transaction_event_attributes(
        required_params={
            "agent": [],
            "user": [],
            "intrinsic": [
                "priority"  # Ensure that priority is set, even if only traceparent is passed.
            ],
        }
    )
    @background_task()
    def _test():
        transaction = current_transaction()

        headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":True,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
        }
        if telemetry == "newrelic":
            headers["tracestate"] = "1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-1-1.23456-1518469636035"
        # "opentelemetry" does not generate tracestate headers

        propagation(headers)
        current_span = otel_api_trace.get_current_span()
        assert transaction.parent_span == "00f067aa0ba902b7"
        assert transaction.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert current_span.get_span_context().trace_id == int("0af7651916cd43dd8448eb211c80319c", 16)

    _test()


@pytest.mark.parametrize("telemetry", ["newrelic", "opentelemetry"])
@pytest.mark.parametrize("propagation", [accept_distributed_trace_headers, PROPAGATOR.extract])
def test_distributed_trace_header_compatibility_partial_granularity(telemetry, propagation):
    """
    Args:
        telemetry (str): either "newrelic" or "opentelemetry"
            Denotes which propagation function was used to
            insert/inject the distributed trace headers.
            "newrelic" => `insert_distributed_trace_headers`
            "opentelemetry" => `PROPAGATOR.inject` from Otel API
        propagation (func): The propagation function to use.
            Either `accept_distributed_trace_headers`
            or `PROPAGATOR.extract`.
    """
    test_settings = _override_settings.copy()
    test_settings.update(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
        }
    )

    @override_application_settings(test_settings)
    @validate_transaction_event_attributes(
        required_params={
            "agent": [],
            "user": [],
            "intrinsic": [
                "priority"  # Ensure that priority is set, even if only traceparent is passed.
            ],
        }
    )
    @background_task()
    def _test():
        transaction = current_transaction()
        headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            "newrelic": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":True,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
        }
        if telemetry == "newrelic":
            headers["tracestate"] = "1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-1-1.23456-1518469636035"
        # "opentelemetry" does not generate tracestate headers

        propagation(headers)
        current_span = otel_api_trace.get_current_span()
        assert transaction.parent_span == "00f067aa0ba902b7"
        assert transaction.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert current_span.get_span_context().trace_id == int("0af7651916cd43dd8448eb211c80319c", 16)

    _test()
