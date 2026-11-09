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
from conftest import CONTEXT_KEY, FLAG_KEY
from opentelemetry import trace as otel_api_trace
from testing_support.fixtures import dt_enabled, override_application_settings, override_generic_settings
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.time_trace import current_trace
from newrelic.core.config import global_settings

FEATURE_FLAG_BASE_ATTRS = {
    "feature_flag.key": FLAG_KEY,
    "feature_flag.provider.name": "LaunchDarkly",
    "feature_flag.context.id": CONTEXT_KEY,
    "feature_flag.result.variationIndex": 0,
    "feature_flag.result.reason.kind": "FALLTHROUGH",
    "feature_flag.result.value": True,
}


@pytest.fixture
def call_instrumentation(tracer):
    @function_trace()
    def foo():
        return current_trace().guid

    def _call_instrumentation():
        # NewRelic instrumented
        trace_guid = foo()

        # OTel instrumented
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            pass

        return trace_guid

    return _call_instrumentation


def test_captures_feature_flag_data_on_span_when_enabled(ld_client, ld_context, call_instrumentation):
    with ld_client() as client:

        @validate_span_events(count=1, exact_users=FEATURE_FLAG_BASE_ATTRS)
        @dt_enabled
        @background_task()
        def test():
            assert client.variation(FLAG_KEY, ld_context, False) is True
            call_instrumentation()

        test()


def test_does_not_capture_feature_flag_data_on_span_when_disabled(
    ld_client, ld_context, ld_spans, call_instrumentation
):
    @override_generic_settings(global_settings(), {"launch_darkly_integration.enabled": False})
    @override_application_settings({"launch_darkly_integration.enabled": False})
    def _test():
        with ld_client() as client:

            @validate_span_events(count=3, unexpected_users=set(FEATURE_FLAG_BASE_ATTRS))
            @dt_enabled
            @background_task()
            def test():
                assert client.variation(FLAG_KEY, ld_context, False) is True
                call_instrumentation()

            test()

    _test()

    assert not ld_spans.spans


def test_captures_falsy_feature_flag_value(ld_client, ld_context):
    with ld_client(configure_flag=lambda flag: flag.variation_for_all(False)) as client:

        @validate_span_events(
            count=1,
            exact_users={
                **FEATURE_FLAG_BASE_ATTRS,
                "feature_flag.result.variationIndex": 1,
                "feature_flag.result.value": False,
            },
        )
        @dt_enabled
        @background_task()
        def test():
            assert client.variation(FLAG_KEY, ld_context, True) is False

        test()


def test_feature_flag_data_forwarded_to_launch_darkly(ld_client, ld_context, ld_spans, call_instrumentation):
    with ld_client() as client:

        @dt_enabled
        @background_task()
        def test():
            assert client.variation(FLAG_KEY, ld_context, False) is True
            return current_trace().guid, call_instrumentation()

        root_guid, child_guid = test()

    spans = {format(span.context.span_id, "016x"): span for span in ld_spans.spans}
    # The OTel span "Bar" is not forwarded.
    assert set(spans) == {root_guid, child_guid}
    root, child = spans[root_guid], spans[child_guid]

    for name, value in FEATURE_FLAG_BASE_ATTRS.items():
        assert root.attributes[name] == value
    assert not any(name.startswith("feature_flag.") for name in child.attributes)

    for span in (root, child):
        assert span.attributes["nr.entity.guid"] == "DEVELOPERMODEENTITYGUID"
        assert span.attributes["nr.entity.url"] == "https://fake-one.newrelic.com/redirect/DEVELOPERMODEENTITYGUID"

    assert child.context.trace_id == root.context.trace_id
    assert child.parent.span_id == root.context.span_id
    assert root.parent is None
