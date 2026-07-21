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

from langchain.messages import HumanMessage

from newrelic.api.background_task import background_task

from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes

recorded_events = [
    [
        {'type': 'LlmTool'},
		{
            'agent_name': 'my_agent',
			'duration': None,
			'id': None,
			'ingest_source': 'Python',
			'input': "{'phrase': 'hello'}",
			'name': 'capitalize_message',
			# 'output': "[{'type': 'text', 'text': 'HELLO', 'id': "
			#           "'lc_3b47afb3-7d8f-4d83-a78f-b1256c17a2f6'}]",
            'output': None,
			'run_id': "tool-id-0",
			'span_id': None,
			'trace_id': None,
			'vendor': 'langchain'
        }
    ],
	[
		{'type': 'LlmChatCompletionSummary'},
		{
            'duration': None,
			'id': None,
			'ingest_source': 'Python',
			'request.model': 'gemini-3.5-flash',
			'request.temperature': 1.0,
			'response.choices.finish_reason': 'STOP',
			'response.model': 'gemini-3.5-flash',
			'response.number_of_messages': 2,
			'response.usage.completion_tokens': 17,
			'response.usage.prompt_tokens': 338,
			'response.usage.total_tokens': 355,
			'span_id': None,
			'time_to_first_token': 3,
			'timestamp': None,
			'trace_id': None,
			'vendor': 'gemini'
        }
    ],
	# [
	# 	{'type': 'LlmChatCompletionMessage'},
	# 	{
    #         'completion_id': None,
	# 		'content': "Take the word hello, capitalize it, then add an exclamation "
	# 		           'point.',
	# 		'id': None,
	# 		'ingest_source': 'Python',
	# 		'response.model': 'gemini-3.5-flash',
	# 		'role': 'user',
	# 		'sequence': 0,
	# 		'span_id': None,
	# 		'timestamp': None,
	# 		'token_count': 0,
	# 		'trace_id': None,
	# 		'vendor': 'gemini'
    #     }
    # ],
	[
		{'type': 'LlmChatCompletionMessage'},
		{
            'completion_id': None,
			'content': 'HELLO',
			'id': None,
			'ingest_source': 'Python',
			'is_response': True,
			'response.model': 'gemini-3.5-flash',
			'role': 'model',
			'sequence': 1,
			'span_id': None,
			'token_count': 0,
			'trace_id': None,
			'vendor': 'gemini'
        }
    ],
	[
		{'type': 'LlmTool'},
		{
            'agent_name': 'my_agent',
			'duration': None,
			'id': None,
			'ingest_source': 'Python',
			'input': "{'phrase': 'HELLO'}",
			'name': 'add_exclamation',
			# 'output': "[{'type': 'text', 'text': 'HELLO!', 'id': "
			#           "'lc_481139a5-95a8-43f6-adda-48e83b5152ae'}]",
            'output': None,
			'run_id': None,
			'span_id': None,
			'trace_id': None,
			'vendor': 'langchain'
        }
    ],
	[
		{'type': 'LlmChatCompletionSummary'},
		{
            'duration': None,
			'id': None,
			'ingest_source': 'Python',
			'request.model': 'gemini-3.5-flash',
			'request.temperature': 1.0,
			'response.choices.finish_reason': 'STOP',
			'response.model': 'gemini-3.5-flash',
			'response.number_of_messages': 2,
			'response.usage.completion_tokens': 15,
			'response.usage.prompt_tokens': 446,
			'response.usage.total_tokens': 461,
			'span_id': None,
			'time_to_first_token': 3,
			'timestamp': None,
			'trace_id': None,
			'vendor': 'gemini'
        }
    ],
	# [
	# 	{'type': 'LlmChatCompletionMessage'},
	# 	{
    #         'completion_id': None,
	# 		'content': "Take the word hello, capitalize it, then add an exclamation "
	# 		           'point.',
	# 		'id': None,
	# 		'ingest_source': 'Python',
	# 		'response.model': 'gemini-3.5-flash',
	# 		'role': 'user',
	# 		'sequence': 0,
	# 		'span_id': None,
	# 		'timestamp': None,
	# 		'token_count': 0,
	# 		'trace_id': None,
	# 		'vendor': 'gemini'
    #     }
    # ],
	[
		{'type': 'LlmChatCompletionMessage'},
		{
            'completion_id': None,
			'content': 'HELLO!',
			'id': None,
			'ingest_source': 'Python',
			'is_response': True,
			'response.model': 'gemini-3.5-flash',
			'role': 'model',
			'sequence': 1,
			'span_id': None,
			'token_count': 0,
			'trace_id': None,
			'vendor': 'gemini'
        }
    ],
	[
		{'type': 'LlmAgent'},
		{
            'duration': None,
			'id': None,
			'ingest_source': 'Python',
			'name': 'my_agent',
			'span_id': None,
			'trace_id': None,
			'vendor': 'langchain'
        }
    ]
]


def _extract_text(message):
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    return ""


chat_astream_metrics = [
    ("Llm/agent/LangChain/astream/my_agent", 1),
    ("Llm/tool/LangChain/arun/capitalize_message", 1),
    ("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/capitalize_message", 1),
    ("Llm/tool/LangChain/arun/add_exclamation", 1),
    ("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/add_exclamation", 1),
    ("Llm/completion/Gemini/generate_content_stream", 3), 
]

@dt_enabled
@reset_core_stats_engine()
@validate_custom_event_count(count=9)
@validate_custom_events(recorded_events)
@validate_transaction_metrics(
    "langchain_integration.test_chat_astream:test_chat_astream",
    scoped_metrics=chat_astream_metrics,
    rollup_metrics=chat_astream_metrics,
    background_task=True,
)
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@validate_span_events(count=2, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@validate_span_events(count=2, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "capitalize_message"}'})
@validate_attributes("agent", ["llm"])
@background_task()
def test_chat_astream(loop, build_agent, async_build_state_graph):
    request_data = "Take the word hello, capitalize it, then add an exclamation point."

    agent = build_agent()
    graph = async_build_state_graph(agent)

    input_state = {"messages": [HumanMessage(content=request_data)]}

    async def graph_astream():
        messages_result = []
        updates_result = []

        async for _, event_type, chunk in graph.astream(input_state, stream_mode=["messages", "updates"], subgraphs=True):
            # Streamed Model Tokens
            if event_type == "messages":
                message_chunk, _ = chunk
                text = _extract_text(message_chunk)
                if text:
                    messages_result.append(text)
            # Node Outputs (including tool results)
            elif event_type == "updates":
                for _, update in chunk.items():
                    if not isinstance(update, dict):
                        continue
                    for msg in update.get("messages", []) or []:
                        if getattr(msg, "type", None) == "tool":
                            updates_result.append(_extract_text(msg))
            
        return messages_result, updates_result
                            
    
    message, updates = loop.run_until_complete(graph_astream())
    assert message[1] == "HELLO!"
    assert updates[1] == "HELLO!"

