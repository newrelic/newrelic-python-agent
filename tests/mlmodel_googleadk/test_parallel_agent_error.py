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

import sys

import pytest
from _test_parallel_agent import (
    LEFT_AGENT_NAME,
    PARALLEL_AGENT_NAME,
    PARALLEL_PROMPT,
    RIGHT_AGENT_NAME,
    build_parallel,
    parallel_recorded_events_error,
)
from conftest import EXPECTED_VERSION_METRICS
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper

EXPECTED_METRICS = [
    (f"Llm/agent/GoogleADK/run_async/{PARALLEL_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{LEFT_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{RIGHT_AGENT_NAME}", 1),
]

EXPECTED_WORKFLOW_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{PARALLEL_AGENT_NAME}"}}'
EXPECTED_LEFT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{LEFT_AGENT_NAME}"}}'
EXPECTED_RIGHT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{RIGHT_AGENT_NAME}"}}'

WORKFLOW_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{PARALLEL_AGENT_NAME}"
LEFT_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{LEFT_AGENT_NAME}"
RIGHT_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{RIGHT_AGENT_NAME}"

# On Python>=3.11, ADK's ParallelAgent uses asyncio.TaskGroup which wraps the child's
# ValueError in an ExceptionGroup, so the parent sees a different error instance from
# the child. As a result, 2 distinct errors are recorded on the transaction.
# On Python<=3.10, ADK re-raises the child's ValueError directly and the
# transaction dedupes the error nodes, so only one error is counted.
EXPECTED_ERROR_EVENT_COUNT = 2 if sys.version_info >= (3, 11) else 1


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(EXPECTED_ERROR_EVENT_COUNT)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(parallel_recorded_events_error)
# 6 events:
#  * 1 LlmAgent workflow event (error)
#  * 1 LlmAgent left child event (error)
#  * 1 LlmAgent right child event (non-error)
#  * 3 LLM events from the right child's Gemini round-trip (Input/Output/Summary)
#  * The failing left child's LLM flow never starts due to the injected exception.
@validate_custom_event_count(6)
@validate_transaction_metrics(
    "test_parallel_agent_error:test_parallel_agent_error",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1,
    exact_intrinsics={"name": WORKFLOW_SPAN_NAME},
    exact_agents={"subcomponent": EXPECTED_WORKFLOW_SUBCOMPONENT},
)
@validate_span_events(
    count=1, exact_intrinsics={"name": LEFT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_LEFT_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": RIGHT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_RIGHT_SUBCOMPONENT}
)
@background_task()
def test_parallel_agent_error(exercise_agent, set_trace_info):
    # Inject a ValueError into the left child's LLM flow only. The right child
    # runs concurrently and completes normally.
    @transient_function_wrapper("google.adk.flows.llm_flows.base_llm_flow", "BaseLlmFlow.run_async")
    def inject_exception(wrapped, instance, args, kwargs):
        invocation_context = args[0] if args else kwargs.get("invocation_context")
        agent = getattr(invocation_context, "agent", None)
        if agent is not None and getattr(agent, "name", None) == LEFT_AGENT_NAME:
            raise ValueError("Oops")
        return wrapped(*args, **kwargs)

    # Catch broad Exception so the test tolerates either a plain ValueError or
    # an ExceptionGroup wrapping one. The validate_error_trace_attributes decorator
    # above asserts the underlying error class.
    @inject_exception
    def _test():
        set_trace_info()
        agent = build_parallel()
        with pytest.raises(Exception):  # noqa: B017
            exercise_agent(agent, PARALLEL_PROMPT)

    _test()
