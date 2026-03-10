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

from opentelemetry import trace

from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_count import validate_transaction_count

from testing_support.util import conditional_decorator
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction


@pytest.mark.parametrize(
    "enabled,traces_enabled",
    [
        (True, True),       # Create and record transaction and trace
        (True, False),      # Do not create transaction
        (False, True),      # Do not create transaction
        (False, False),     # Do not create transaction
    ]
)
def test_opentelemetry_bridge_enabled(enabled, traces_enabled):
    @override_application_settings(
        {
            "opentelemetry.enabled": enabled,
            "opentelemetry.traces.enabled": traces_enabled
        }
    )
    @dt_enabled
    @conditional_decorator(
        condition=(enabled and traces_enabled),
        decorator=validate_transaction_metrics(name="Bar")
    )
    @conditional_decorator(
        condition=(enabled and traces_enabled),
        decorator=validate_span_events(count=1, exact_intrinsics={"name": "Function/Bar"})
    )
    @conditional_decorator(
        condition=(enabled and traces_enabled),
        decorator=validate_span_events(count=1, exact_intrinsics={"name": "Function/Baz"})
    )
    @conditional_decorator(
        condition=(not enabled or not traces_enabled),
        decorator=validate_transaction_count(count=0)
    )
    def _test():
        tracer = trace.get_tracer_provider().get_tracer("Tracer")
        
        with tracer.start_as_current_span(name="Bar", kind=trace.SpanKind.SERVER) as bar_span:
            bar_span_id = bar_span.get_span_context().span_id
            bar_trace_id = bar_span.get_span_context().trace_id

            with tracer.start_as_current_span(name="Baz", kind=trace.SpanKind.SERVER) as baz_span:
                nr_trace = current_trace()
                nr_transaction = current_transaction()
                baz_span_id = baz_span.get_span_context().span_id
                baz_trace_id = baz_span.get_span_context().trace_id

                assert bar_trace_id == baz_trace_id

                if enabled and traces_enabled:
                    assert bar_trace_id == baz_trace_id == int(nr_transaction.trace_id, 16)
                    assert baz_span_id == int(nr_trace.guid, 16)
                    assert bar_span_id == int(nr_trace.parent.guid, 16)
                    assert nr_trace is not nr_trace.root

                else:
                    assert bar_trace_id == baz_trace_id == 0
                    assert baz_span_id == bar_span_id == 0
                    assert nr_trace is None

    _test()


@pytest.mark.parametrize(
    "enabled,include,exclude,expected_foo_span_count,expected_bar_span_count",
    [
        (True, set(), {"some_tracer"}, 1, 1),                   # Invalid tracer name in exclude
        (True, {"some_tracer"}, set(), 1, 1),                   # Invalid tracer name in include
        (True, {"FirstTracer"}, {"FirstTracer"}, 0, 1),         # Exclude `FirstTracer` tracer.  Takes priority over include
        (True, set(), {"SecondTracer"}, 1, 0),                  # Exclude `SecondTracer` tracer
        (True, None, {"SecondTracer"}, 1, 0),                   # Exclude `SecondTracer` tracer, include set to `None`
        (True, set(), {"FirstTracer","SecondTracer"}, 0, 0),    # Exclude both tracers
        (False, {"FirstTracer"}, {"SecondTracer"}, 0, 0),       # Disabled
    ],
    ids=[
        "include=(empty set),exclude=(invalid name)",
        "include=(invalid name),exclude=(empty set)",
        "include=FirstTracer,exclude=FirstTracer",
        "include=(empty set),exclude=SecondTracer",
        "include=None,exclude=SecondTracer",
        "include=(empty set),exclude=FirstTracer,SecondTracer",
        "disabled",
    ],
)
def test_opentelemetry_tracer_include_and_exclude(enabled, include, exclude, expected_foo_span_count, expected_bar_span_count):
    tracer1 = trace.get_tracer_provider().get_tracer("FirstTracer")
    tracer2 = trace.get_tracer_provider().get_tracer("SecondTracer")
    
    @override_application_settings(
        {
            "opentelemetry.traces.enabled": enabled,
            "opentelemetry.traces.include": include,
            "opentelemetry.traces.exclude": exclude,
        }
    )
    @dt_enabled
    @conditional_decorator(
        condition=expected_foo_span_count,
        decorator=validate_span_events(count=1, exact_intrinsics={"name": "Function/Foo"})
    )
    @conditional_decorator(
        condition=expected_bar_span_count,
        decorator=validate_span_events(count=1, exact_intrinsics={"name": "Function/Bar"})
    )
    @validate_transaction_count(count=int(expected_foo_span_count or expected_bar_span_count))
    def _test():
        with tracer1.start_as_current_span(name="Foo", kind=trace.SpanKind.SERVER):
            with tracer2.start_as_current_span(name="Bar", kind=trace.SpanKind.SERVER):
                pass

    _test()


def test_opentelemetry_tracer_nested_include_and_exclude():
    tracer1 = trace.get_tracer_provider().get_tracer("FirstTracer")
    tracer2 = trace.get_tracer_provider().get_tracer("SecondTracer")
    
    @override_application_settings(
        {
            "opentelemetry.traces.exclude": {"SecondTracer"},
        }
    )
    @dt_enabled
    @validate_span_events(count=1, exact_intrinsics={"name": "Function/Foo"})
    @validate_span_events(count=1, exact_intrinsics={"name": "Function/Baz"})
    @validate_span_events(count=2)  # Ensure the disabled tracer's span does not raise the count to 3
    def _test():
        with tracer1.start_as_current_span(name="Foo", kind=trace.SpanKind.SERVER) as foo_span:
            nr_foo_trace_guid = int(current_trace().guid, 16)
            foo_span_id = foo_span.get_span_context().span_id
            assert nr_foo_trace_guid == foo_span_id
            
            with tracer2.start_as_current_span(name="Bar", kind=trace.SpanKind.SERVER) as bar_span:
                nr_bar_trace_guid = int(current_trace().guid, 16)
                bar_span_id = bar_span.get_span_context().span_id
                # This tracer is disabled, so the current
                # trace/span is actually the trace created above.
                assert nr_foo_trace_guid == nr_bar_trace_guid
                assert nr_bar_trace_guid == bar_span_id
                
                with tracer1.start_as_current_span(name="Baz", kind=trace.SpanKind.SERVER) as baz_span:
                    nr_baz_trace_guid = int(current_trace().guid, 16)
                    nr_parent_trace_guid = int(current_trace().parent.guid, 16)
                    baz_span_id = baz_span.get_span_context().span_id
                    assert nr_foo_trace_guid == nr_parent_trace_guid
                    assert nr_baz_trace_guid == baz_span_id

    _test()
