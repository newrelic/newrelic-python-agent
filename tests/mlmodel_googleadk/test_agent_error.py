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
from _test_agent import AGENT_NAME, agent_recorded_event_error, build_agent
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

EXPECTED_AGENT_METRIC = (f"Llm/agent/GoogleADK/google.adk.agents.llm_agent:LlmAgent._run_async_impl/{AGENT_NAME}", 1)


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(agent_recorded_event_error)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    "test_agent_error:test_agent_error",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@background_task()
def test_agent_error(exercise_agent, set_trace_info):
    # Inject a ValueError inside _run_async_impl's async iteration
    # so the exception flows through the async generator's athrow.
    @transient_function_wrapper("google.adk.flows.llm_flows.base_llm_flow", "BaseLlmFlow.run_async")
    def inject_exception(wrapped, instance, args, kwargs):
        raise ValueError("Oops")

    @inject_exception
    def _test():
        set_trace_info()
        agent = build_agent()
        with pytest.raises(ValueError):
            exercise_agent(agent, "trigger error")

    _test()
