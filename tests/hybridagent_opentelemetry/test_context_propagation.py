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

from opentelemetry import trace as otel_api_trace, propagate as otel_api_propagate

from newrelic.api.transaction import (
    accept_distributed_trace_headers,
    current_transaction,
)
from newrelic.api.background_task import background_task

from testing_support.fixtures import (
    override_application_settings,
)

PROPAGATOR = otel_api_propagate.get_global_textmap()

_override_settings = {
    "trusted_account_key": "1",
    "distributed_tracing.enabled": True,
    "span_events.enabled": True,
}


@pytest.mark.parametrize(
    "telemetry,web_headers,propagation",
    (
        (
            "newrelic",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "newrelic",
            True,
            PROPAGATOR.extract,
        ),
        (
            "newrelic",
            False,
            PROPAGATOR.extract,
        ),
        (
            "hybrid_otel",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "hybrid_otel",
            True,
            PROPAGATOR.extract,
        ),
        (
            "hybrid_otel",
            False,
            PROPAGATOR.extract,
        ),
        (
            "pure_otel",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "pure_otel",
            True,
            PROPAGATOR.extract,
        ),
        (
            "pure_otel",
            False,
            PROPAGATOR.extract,
        ),
    )
)
def test_distributed_trace_tracestate_compatibility_full_granularity(
    telemetry, web_headers, propagation
):
    """
    Args:
        telemetry (str): either "newrelic", "hybrid_otel", or "pure_otel"
            Denotes which propagation function was used to 
            insert/inject the distributed trace headers.
            "newrelic" => `insert_distributed_trace_headers`
            "hybrid_otel" => `PROPAGATOR.inject` from Hybrid Agent
            "pure_otel" => `PROPAGATOR.inject` from OTel SDK
        web_headers (bool): For OTel web framework instrumentation, 
            header keys will be captalized and prepended with "HTTP_".
            Only applicable for headers coming from OTel
        propagation (func): The propagation function to use.
            Either `accept_distributed_trace_headers`
            or `PROPAGATOR.extract`.  Note: If using 
            `accept_distributed_trace_headers`, the web_headers
            flag must be false.
            
    """
    @override_application_settings(_override_settings)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        transaction = current_transaction()
        
        headers = {
            f"{'HTTP_TRACEPARENT' if web_headers else 'traceparent'}": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            f"{'HTTP_NEWRELIC' if web_headers else 'newrelic'}": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":True,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
        }
        if telemetry == "newrelic":
            headers[
                f"{'HTTP_TRACESTATE' if web_headers else 'tracestate'}"
            ] = "1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-1-1.23456-1518469636035"
        elif telemetry == "hybrid_otel":
            headers[
                f"{'HTTP_TRACESTATE' if web_headers else 'tracestate'}"
            ] = "ac=1,ap=2827902,tx=0af7651916cd43dd,id=00f067aa0ba902b7,sa=True,pr=1.23456,ti=1518469636035,tr=0af7651916cd43dd8448eb211c80319c"
        # "pure_otel" has no tracestate headers
        
        propagation(headers)
        current_span = otel_api_trace.get_current_span()
        assert transaction.parent_span == "00f067aa0ba902b7"
        assert transaction.trace_id == "0af7651916cd43dd8448eb211c80319c"
        current_span.get_span_context().trace_id == int("0af7651916cd43dd8448eb211c80319c", 16)
        
        # Ensure that priority gets set despite having
        # the sample flag set but no priority set
        assert transaction.priority

    _test()
    

@pytest.mark.parametrize(
    "telemetry,web_headers,propagation",
    (
        (
            "newrelic",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "newrelic",
            True,
            PROPAGATOR.extract,
        ),
        (
            "newrelic",
            False,
            PROPAGATOR.extract,
        ),
        (
            "hybrid_otel",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "hybrid_otel",
            True,
            PROPAGATOR.extract,
        ),
        (
            "hybrid_otel",
            False,
            PROPAGATOR.extract,
        ),
        (
            "pure_otel",
            False,
            accept_distributed_trace_headers,
        ),
        (
            "pure_otel",
            True,
            PROPAGATOR.extract,
        ),
        (
            "pure_otel",
            False,
            PROPAGATOR.extract,
        ),
    )
)
def test_distributed_trace_tracestate_compatibility_partial_granularity(
    telemetry, web_headers, propagation
):
    """
    Args:
        telemetry (str): either "newrelic", "hybrid_otel", or "pure_otel"
            Denotes which propagation function was used to 
            insert/inject the distributed trace headers.
            "newrelic" => `insert_distributed_trace_headers`
            "hybrid_otel" => `PROPAGATOR.inject` from Hybrid Agent
            "pure_otel" => `PROPAGATOR.inject` from OTel SDK
        web_headers (bool): For OTel web framework instrumentation, 
            header keys will be captalized and prepended with "HTTP_".
            Only applicable for headers coming from OTel
        propagation (func): The propagation function to use.
            Either `accept_distributed_trace_headers`
            or `PROPAGATOR.extract`.  Note: If using 
            `accept_distributed_trace_headers`, the web_headers
            flag must be false.
            
    """
    test_settings = _override_settings.copy()
    test_settings.update(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
        }
    )
    @override_application_settings(test_settings)
    @background_task(name="test_distributed_trace_attributes")
    def _test():
        transaction = current_transaction()
        
        headers = {
            f"{'HTTP_TRACEPARENT' if web_headers else 'traceparent'}": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            f"{'HTTP_NEWRELIC' if web_headers else 'newrelic'}": '{"v":[0,1],"d":{"ty":"Mobile","ac":"123","ap":"51424","id":"5f474d64b9cc9b2a","tr":"6e2fea0b173fdad0","pr":0.1234,"sa":True,"ti":1482959525577,"tx":"27856f70d3d314b7"}}',  # This header should be ignored.
        }
        if telemetry == "newrelic":
            headers[
                f"{'HTTP_TRACESTATE' if web_headers else 'tracestate'}"
            ] = "1@nr=0-0-1-2827902-0af7651916cd43dd-00f067aa0ba902b7-1-1.23456-1518469636035"
        elif telemetry == "hybrid_otel":
            headers[
                f"{'HTTP_TRACESTATE' if web_headers else 'tracestate'}"
            ] = "ac=1,ap=2827902,tx=0af7651916cd43dd,id=00f067aa0ba902b7,sa=True,pr=1.23456,ti=1518469636035,tr=0af7651916cd43dd8448eb211c80319c"
        # "pure_otel" has no tracestate headers
        
        propagation(headers)
        current_span = otel_api_trace.get_current_span()
        assert transaction.parent_span == "00f067aa0ba902b7"
        assert transaction.trace_id == "0af7651916cd43dd8448eb211c80319c"
        current_span.get_span_context().trace_id == int("0af7651916cd43dd8448eb211c80319c", 16)
        
        # Ensure that priority gets set despite having
        # the sample flag set but no priority set
        assert transaction.priority

    _test()
    
