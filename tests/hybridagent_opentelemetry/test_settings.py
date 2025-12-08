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
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction


@pytest.mark.parametrize("enabled", [True, False])
def test_distributed_tracing_enabled(tracer, enabled):
    @override_application_settings({"otel_bridge.enabled": enabled})
    @validate_span_events(count=1, exact_intrinsics={"name": "Function/Foo"})
    @validate_span_events(count=1 if enabled else 0, exact_intrinsics={"name": "Function/Bar"})
    @validate_span_events(count=1 if enabled else 0, exact_intrinsics={"name": "Function/Baz"})
    @background_task(name="Foo")
    def _test():
        with tracer.start_as_current_span(name="Bar") as bar_span:
            bar_span_id = bar_span.get_span_context().span_id
            bar_trace_id = bar_span.get_span_context().trace_id

            with tracer.start_as_current_span(name="Baz") as baz_span:
                nr_trace = current_trace()
                nr_transaction = current_transaction()
                baz_span_id = baz_span.get_span_context().span_id
                baz_trace_id = baz_span.get_span_context().trace_id

                assert bar_trace_id == baz_trace_id

                if enabled:
                    assert bar_trace_id == baz_trace_id == int(nr_transaction.trace_id, 16)
                    assert baz_span_id == int(nr_trace.guid, 16)
                    assert bar_span_id == int(nr_trace.parent.guid, 16)
                    assert nr_trace is not nr_trace.root

                else:
                    assert bar_trace_id == baz_trace_id == 0
                    assert baz_span_id == bar_span_id == 0
                    assert nr_trace is nr_trace.root

    _test()
