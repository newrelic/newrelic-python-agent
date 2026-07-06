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
from _test_sub_agent import CHILD_AGENT_NAME, PARENT_AGENT_NAME, PROMPT, build_sub_agent, sub_agent_recorded_event_error
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
    (f"Llm/agent/GoogleADK/run_async/{PARENT_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{CHILD_AGENT_NAME}", 1),
]

EXPECTED_PARENT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{PARENT_AGENT_NAME}"}}'
EXPECTED_CHILD_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{CHILD_AGENT_NAME}"}}'

PARENT_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{PARENT_AGENT_NAME}"
CHILD_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{CHILD_AGENT_NAME}"


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(sub_agent_recorded_event_error)
# 6 events:
#  * 1 LlmAgent parent event
#  * 1 LlmAgent child event
#  * 1 LlmTool event (transfer_to_agent)
#  * 3 LLM events from the parent's Gemini round trip (Input/Output/Summary)
#  * The child's LLM flow never runs due to the injected error, so no LLM events.
@validate_custom_event_count(6)
@validate_transaction_metrics(
    "test_sub_agent_error:test_sub_agent_error",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1, exact_intrinsics={"name": PARENT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_PARENT_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": CHILD_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_CHILD_SUBCOMPONENT}
)
@background_task()
def test_sub_agent_error(exercise_agent, set_trace_info):
    # Inject a ValueError scoped to the child agent's flow only, gated on the
    # invocation_context's agent name. The parent's LLM call completes successfully first,
    # then the transfer_to_agent tool completes successfully. After the transfer,
    # ADK attempts to run the child which raises the exception and sees the error.
    @transient_function_wrapper("google.adk.flows.llm_flows.base_llm_flow", "BaseLlmFlow.run_async")
    def inject_exception(wrapped, instance, args, kwargs):
        invocation_context = args[0] if args else kwargs.get("invocation_context")
        agent = getattr(invocation_context, "agent", None)
        if agent is not None and getattr(agent, "name", None) == CHILD_AGENT_NAME:
            raise ValueError("Oops")
        return wrapped(*args, **kwargs)

    @inject_exception
    def _test():
        set_trace_info()
        agent = build_sub_agent()
        with pytest.raises(ValueError):
            exercise_agent(agent, PROMPT)

    _test()
