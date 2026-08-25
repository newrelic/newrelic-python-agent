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
import ldclient
from ldclient.integrations.test_data import TestData
from ldobserve import ObservabilityConfig, ObservabilityPlugin
from testing_support.validators.validate_span_events import validate_span_events
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from opentelemetry import trace as otel_api_trace

@pytest.fixture
def call_instrumentation(tracer):
    @function_trace()
    def foo():
        pass

    def _call_instrumentation():
        # NewRelic instrumented
        foo()

        # OTel instrumented
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            pass

    return _call_instrumentation


@pytest.fixture
def evaluate_feature_flag():
    def _evaluate_feature_flag():
        context = ldclient.Context.builder("send-request") \
            .set("firstName", "Sandy") \
            .set("lastName", "Smith") \
            .set("email", "sandy@example.com") \
            .set("groups", ["Acme", "Global Health Services"]) \
            .build()
        flag_value = ldclient.get().variation("send-request", context, False)
        return flag_value

    return _evaluate_feature_flag


@pytest.fixture
def initialize_ldclient():
    # In-memory flag data source: avoids any real streaming/polling connection
    # to LaunchDarkly while still running real flag-rule evaluation logic.
    td = TestData.data_source()
    td.update(td.flag("send-request").variation_for_all(True))

    observability_config = ObservabilityConfig(
      service_name="hstepanek-proto",
      service_version="0.0.0",
      # Avoid ldobserve's own background exporter reaching real LaunchDarkly
      # observability endpoints.
      otlp_endpoint="http://localhost:4317",
      backend_url="http://localhost:4317",
      disable_export_error_logging=True,
    )
    plugin = ObservabilityPlugin(observability_config)
    ldclient.set_config(
        ldclient.config.Config(
            "super-secret-sdk-key",
            update_processor_class=td,
            send_events=False,
            diagnostic_opt_out=True,
            plugins=[plugin],
        )
    )

    assert ldclient.get().is_initialized()

    yield

    ldclient._reset_client()


@validate_span_events(
    count=1,
    exact_users={
        'feature_flag.key': "send-request",
        'feature_flag.provider.name': 'LaunchDarkly',
        'feature_flag.context.id': "send-request",
        'feature_flag.result.variationIndex': 0,
        'feature_flag.result.reason.kind': "FALLTHROUGH",
        #'feature_flag.result.reason.inExperiment': True,
        'feature_flag.result.value': True,
    }
)
@background_task()
def test_captures_feature_flag_data_on_span(evaluate_feature_flag, call_instrumentation, initialize_ldclient):
    flag_value = evaluate_feature_flag()
    if flag_value:
        call_instrumentation()

