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

# Ignore unicode characters in this file from LLM responses
# ruff: noqa: RUF001

chat_completion_expected_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "duration": None,  # Response time varies each test run
            "request.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "max_tokens",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "To convert 212°F to Celsius, we can use the formula:\n\nC = (F - 32) × 5/9\n\nWhere:\nC is the temperature in Celsius\nF is the temperature in Fahrenheit\n\nPlugging in 212°F, we get:\n\nC = (212 - 32) × 5/9\nC = 180 × 5/9\nC = 100\n\nTherefore, 212°",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "is_response": True,
        },
    ),
]

chat_completion_expected_streaming_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f070b880-e0fb-4537-8093-796671c39239",
            "duration": None,  # Response time varies each test run
            "request.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "max_tokens",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f070b880-e0fb-4537-8093-796671c39239",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f070b880-e0fb-4537-8093-796671c39239",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f070b880-e0fb-4537-8093-796671c39239",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "To convert Fahrenheit to Celsius, you use the formula:\n\nC = (F - 32) * 5/9\n\nWhere:\nC is the temperature in Celsius\nF is the temperature in Fahrenheit\n\nPlugging in 212°F for F:\n\nC = (212 - 32) * 5/9\nC = 180 * 5/9\nC = 100\n\nTherefore, 212 degrees Fahren",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "is_response": True,
        },
    ),
]

chat_completion_invalid_access_key_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "e1206e19-2318-4a9d-be98-017c73f06118",
            "duration": None,  # Response time varies each test run
            "request.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "e1206e19-2318-4a9d-be98-017c73f06118",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "Invalid Token",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]
chat_completion_invalid_model_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.model": "does-not-exist",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "content": "Model does not exist.",
            "role": "user",
            "completion_id": None,
            "response.model": "does-not-exist",
            "sequence": 0,
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]
