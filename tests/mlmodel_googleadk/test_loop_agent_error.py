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
from _test_loop_agent import LOOP_AGENT_NAME, LOOP_PROMPT, LOOPED_AGENT_NAME, build_loop, loop_recorded_events_error
from conftest import EXPECTED_GOOGLE_ADK_VERSION_METRIC
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
    (f"Llm/agent/GoogleADK/run_async/{LOOP_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{LOOPED_AGENT_NAME}", 1),
]

EXPECTED_WORKFLOW_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{LOOP_AGENT_NAME}"}}'
EXPECTED_CHILD_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{LOOPED_AGENT_NAME}"}}'

WORKFLOW_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{LOOP_AGENT_NAME}"
CHILD_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{LOOPED_AGENT_NAME}"


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(loop_recorded_events_error)
# 2 events:
#  * 1 LlmAgent workflow event (error=True)
#  * 1 LlmAgent child event (exits after first iteration)
#  * The child's LLM flow never starts due to the injected error, so no LLM events.
@validate_custom_event_count(2)
@validate_transaction_metrics(
    "test_loop_agent_error:test_loop_agent_error",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=[EXPECTED_GOOGLE_ADK_VERSION_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1,
    exact_intrinsics={"name": WORKFLOW_SPAN_NAME},
    exact_agents={"subcomponent": EXPECTED_WORKFLOW_SUBCOMPONENT},
)
@validate_span_events(
    count=1, exact_intrinsics={"name": CHILD_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_CHILD_SUBCOMPONENT}
)
@background_task()
def test_loop_agent_error(exercise_agent, set_trace_info):
    # Inject a ValueError into the child's flow only. BaseLlmFlow.run_async is
    # shared across all LlmAgents, so we gate the raise on the invocation_context's
    # agent name. The loop terminates on the first iteration's exception.
    @transient_function_wrapper("google.adk.flows.llm_flows.base_llm_flow", "BaseLlmFlow.run_async")
    def inject_exception(wrapped, instance, args, kwargs):
        invocation_context = args[0] if args else kwargs.get("invocation_context")
        agent = getattr(invocation_context, "agent", None)
        if agent is not None and getattr(agent, "name", None) == LOOPED_AGENT_NAME:
            raise ValueError("Oops")
        return wrapped(*args, **kwargs)

    @inject_exception
    def _test():
        set_trace_info()
        agent = build_loop()
        with pytest.raises(ValueError):
            exercise_agent(agent, LOOP_PROMPT)

    _test()
