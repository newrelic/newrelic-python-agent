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

# COME BACK TO THIS AND TEST WITH THE API AND SDK AND
# SEE IF THE MONKEY PATCHING WORKS IN ADDITION TO SETTING
# UP THE TRACER PROVIDER (which for NR should not do anything)


# from opentelemetry import trace
# from opentelemetry.sdk.trace import TracerProvider

# from newrelic.api.background_task import background_task
from newrelic.hooks.hybridagent_opentelemetry import Tracer

# from testing_support.validators.validate_span_events import validate_span_events


# from opentelemetry.sdk.trace.export import (
#     BatchSpanProcessor,
#     ConsoleSpanExporter,
# )


def test_trace_basic():
    tracer = Tracer()

    with tracer.start_as_current_span("foo"):
        pass


# provider = TracerProvider()
# # processor = BatchSpanProcessor(ConsoleSpanExporter())
# # provider.add_span_processor(processor)
# trace.set_tracer_provider(provider)


# @background_task()
# def test_trace_basic():
#     tracer = trace.get_tracer("TracerProviderTestBasic")

#     with tracer.start_as_current_span("foo"):
#         pass


# @validate_span_events(
#     count=1,
#     exact_users={"name": "opentelemetry.sdk.trace:Tracer.start_span/foo",
#                  "otel_trace_id": None,
#                  "otel_span_id": None,
#                  },
# )
# @background_task()
def test_trace_nested():
    # tracer = trace.get_tracer("TracerProviderTestNested")
    tracer = Tracer()

    with tracer.start_as_current_span("foo"):
        with tracer.start_as_current_span("bar"):
            with tracer.start_as_current_span("baz"):
                pass
