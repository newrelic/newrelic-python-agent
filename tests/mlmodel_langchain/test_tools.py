# # Copyright 2010 New Relic, Inc.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #      http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

# import pytest
# from testing_support.fixtures import reset_core_stats_engine, validate_attributes
# from testing_support.ml_testing_utils import (
#     disabled_ai_monitoring_record_content_settings,
#     events_with_context_attrs,
#     tool_events_sans_content,
# )
# from testing_support.validators.validate_custom_event import validate_custom_event_count
# from testing_support.validators.validate_custom_events import validate_custom_events
# from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
# from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
# from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

# from newrelic.api.background_task import background_task
# from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
# from newrelic.common.object_names import callable_name
# from newrelic.common.object_wrapper import transient_function_wrapper

# from ._test_tools import add_exclamation, single_tool_model, single_tool_model_error

# tool_recorded_event = [
#     (
#         {"type": "LlmTool"},
#         {
#             "id": None,
#             "run_id": "123",
#             "output": "{'text': 'Hello!'}",
#             "name": "add_exclamation",
#             "agent_name": "my_agent",
#             "span_id": None,
#             "trace_id": "trace-id",
#             "input": "{'message': 'Hello'}",
#             "vendor": "strands",
#             "ingest_source": "Python",
#             "duration": None,
#         },
#     )
# ]

# tool_recorded_event_forced_internal_error = [
#     (
#         {"type": "LlmTool"},
#         {
#             "id": None,
#             "run_id": "123",
#             "name": "add_exclamation",
#             "agent_name": "my_agent",
#             "span_id": None,
#             "trace_id": "trace-id",
#             "input": "{'message': 'Hello'}",
#             "vendor": "strands",
#             "ingest_source": "Python",
#             "duration": None,
#             "error": True,
#         },
#     )
# ]

# tool_recorded_event_error_coro = [
#     (
#         {"type": "LlmTool"},
#         {
#             "id": None,
#             "run_id": "123",
#             "name": "add_exclamation",
#             "agent_name": "my_agent",
#             "span_id": None,
#             "trace_id": "trace-id",
#             "input": "{'message': 'exc'}",
#             "vendor": "strands",
#             "ingest_source": "Python",
#             "error": True,
#             "output": "{'text': 'Error: RuntimeError - Oops'}",
#             "duration": None,
#         },
#     )
# ]


# @reset_core_stats_engine()
# @validate_custom_events(events_with_context_attrs(tool_recorded_event))
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_strands.test_tools:test_tool",
#     scoped_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     rollup_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
# @background_task()
# def test_tool(exercise_agent, set_trace_info, single_tool_model, add_exclamation):
#     set_trace_info()
#     my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

#     with WithLlmCustomAttributes({"context": "attr"}):
#         response = exercise_agent(my_agent, 'Add an exclamation to the word "Hello"')

#     if isinstance(response, list):
#         # Streaming returns a list of events
#         messages = [event["message"]["content"] for event in response if "message" in event]
#         assert len(messages) == 3
#         assert messages[0][0]["text"] == "Calling add_exclamation tool"
#         assert messages[0][1]["toolUse"]["name"] == "add_exclamation"
#         assert messages[1][0]["toolResult"]["content"][0]["text"] == "Hello!"
#         assert messages[2][0]["text"] == "Success!"
#     else:
#         # Invoke returns a response object
#         assert response.message["content"][0]["text"] == "Success!"
#         assert response.metrics.tool_metrics["add_exclamation"].success_count == 1


# @reset_core_stats_engine()
# @disabled_ai_monitoring_record_content_settings
# @validate_custom_events(tool_events_sans_content(tool_recorded_event))
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_strands.test_tools:test_tool_no_content",
#     scoped_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     rollup_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
# @background_task()
# def test_tool_no_content(exercise_agent, set_trace_info, single_tool_model, add_exclamation):
#     set_trace_info()
#     my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

#     response = exercise_agent(my_agent, 'Add an exclamation to the word "Hello"')

#     if isinstance(response, list):
#         # Streaming returns a list of events
#         messages = [event["message"]["content"] for event in response if "message" in event]
#         assert len(messages) == 3
#         assert messages[0][0]["text"] == "Calling add_exclamation tool"
#         assert messages[0][1]["toolUse"]["name"] == "add_exclamation"
#         assert messages[1][0]["toolResult"]["content"][0]["text"] == "Hello!"
#         assert messages[2][0]["text"] == "Success!"
#     else:
#         # Invoke returns a response object
#         assert response.message["content"][0]["text"] == "Success!"
#         assert response.metrics.tool_metrics["add_exclamation"].success_count == 1


# @reset_core_stats_engine()
# @validate_transaction_error_event_count(1)
# @validate_error_trace_attributes(callable_name(RuntimeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
# @validate_custom_events(tool_recorded_event_error_coro)
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_strands.test_tools:test_tool_execution_error",
#     scoped_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     rollup_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
# @background_task()
# def test_tool_execution_error(exercise_agent, set_trace_info, single_tool_model_error, add_exclamation):
#     set_trace_info()
#     my_agent = Agent(name="my_agent", model=single_tool_model_error, tools=[add_exclamation])

#     response = exercise_agent(my_agent, 'Add an exclamation to the word "exc"')

#     if isinstance(response, list):
#         # Streaming returns a list of events
#         messages = [event["message"]["content"] for event in response if "message" in event]
#         assert len(messages) == 3
#         assert messages[0][0]["text"] == "Calling add_exclamation tool"
#         assert messages[0][1]["toolUse"]["name"] == "add_exclamation"
#         assert messages[1][0]["toolResult"]["content"][0]["text"] == "Error: RuntimeError - Oops"
#         assert messages[2][0]["text"] == "Success!"
#     else:
#         # Invoke returns a response object
#         assert response.message["content"][0]["text"] == "Success!"
#         assert response.metrics.tool_metrics["add_exclamation"].error_count == 1


# @reset_core_stats_engine()
# @validate_transaction_error_event_count(1)
# @validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
# @validate_custom_events(tool_recorded_event_forced_internal_error)
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_strands.test_tools:test_tool_pre_execution_exception",
#     scoped_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     rollup_metrics=[("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
# @background_task()
# def test_tool_pre_execution_exception(exercise_agent, set_trace_info, single_tool_model, add_exclamation):
#     # Add a wrapper to intentionally force an error in the ToolExecutor._stream code to hit the exception path in
#     # the AsyncGeneratorProxy
#     # TODO: Find somewhere to inject this in langchain. This was from strands.
#     @transient_function_wrapper("strands.hooks.events", "BeforeToolCallEvent.__init__")
#     def _wrap_BeforeToolCallEvent_init(wrapped, instance, args, kwargs):
#         raise ValueError("Oops")

#     @_wrap_BeforeToolCallEvent_init
#     def _test():
#         set_trace_info()
#         my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])
#         return exercise_agent(my_agent, 'Add an exclamation to the word "Hello"')

#     # This will not explicitly raise a ValueError when running the test but we are still able to  capture it in the error trace
#     response = _test()

#     if isinstance(response, list):
#         # Streaming returns a list of events
#         messages = [event["message"]["content"] for event in response if "message" in event]
#         assert len(messages) == 3
#         assert messages[0][0]["text"] == "Calling add_exclamation tool"
#         assert messages[0][1]["toolUse"]["name"] == "add_exclamation"
#         assert not messages[1], "Failed tool invocation should return an empty message."
#         assert messages[2][0]["text"] == "Success!"
#     else:
#         # Invoke returns a response object
#         assert response.message["content"][0]["text"] == "Success!"
#         assert not response.metrics.tool_metrics
