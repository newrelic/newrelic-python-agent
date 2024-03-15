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

chat_completion_payload_templates = {
    "amazon.titan-text-express-v1": '{ "inputText": "%s", "textGenerationConfig": {"temperature": %f, "maxTokenCount": %d }}',
    "ai21.j2-mid-v1": '{"prompt": "%s", "temperature": %f, "maxTokens": %d}',
    "anthropic.claude-instant-v1": '{"prompt": "Human: %s Assistant:", "temperature": %f, "max_tokens_to_sample": %d}',
    "cohere.command-text-v14": '{"prompt": "%s", "temperature": %f, "max_tokens": %d}',
    "meta.llama2-13b-chat-v1": '{"prompt": "%s", "temperature": %f, "max_gen_len": %d}',
}

chat_completion_expected_events = {
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
                "response.usage.completion_tokens": 32,
                "response.usage.total_tokens": 44,
                "response.usage.prompt_tokens": 12,
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "FINISH",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "\n1 degree Fahrenheit is 0.56 Celsius. Therefore, 212 degree Fahrenheit in Celsius would be 115.42.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "ai21.j2-mid-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "228ee63f-4eca-4b7d-b679-bc920de63525",
                "response_id": "1234",
                "duration": None,  # Response time varies each test run
                "request.model": "ai21.j2-mid-v1",
                "response.model": "ai21.j2-mid-v1",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "endoftext",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": "1234-0",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "228ee63f-4eca-4b7d-b679-bc920de63525",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "ai21.j2-mid-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": "1234-1",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "228ee63f-4eca-4b7d-b679-bc920de63525",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "\n212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "ai21.j2-mid-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "anthropic.claude-instant-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "6a886158-b39f-46ce-b214-97458ab76f2f",
                "duration": None,  # Response time varies each test run
                "request.model": "anthropic.claude-instant-v1",
                "response.model": "anthropic.claude-instant-v1",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "max_tokens",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "6a886158-b39f-46ce-b214-97458ab76f2f",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Human: What is 212 degrees Fahrenheit converted to Celsius? Assistant:",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "anthropic.claude-instant-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "6a886158-b39f-46ce-b214-97458ab76f2f",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": " Okay, here are the steps to convert 212 degrees Fahrenheit to Celsius:\n\n1) The formula to convert between Fahrenheit and Celsius is:\n   C = (F - 32) * 5/9\n\n2) Plug in 212 degrees Fahrenheit for F:\n   C = (212 - 32) * 5/9\n   C = 180 * 5/9\n   C = 100\n\n3) Therefore, 212 degrees Fahrenheit converted to Celsius is 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "anthropic.claude-instant-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "cohere.command-text-v14": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "12912a17-aa13-45f3-914c-cc82166f3601",
                "response_id": None,  # UUID that varies with each run
                "duration": None,  # Response time varies each test run
                "request.model": "cohere.command-text-v14",
                "response.model": "cohere.command-text-v14",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "MAX_TOKENS",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "12912a17-aa13-45f3-914c-cc82166f3601",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "12912a17-aa13-45f3-914c-cc82166f3601",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": " To convert from Fahrenheit to Celsius, you can use the following formula:\n\nCelsius = (Fahrenheit - 32) * 5/9\n\nIn this case, 212 degrees Fahrenheit is converted to Celsius as follows:\n\nCelsius = (212 - 32) * 5/9 = (180) * 5/9 = (180/9) = 20 degrees Celsius\n\nTherefore, 212 degrees Fahrenheit is equivalent to 20 degrees Celsius.\n\nIt's important to note that",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "meta.llama2-13b-chat-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "a168214d-742d-4244-bd7f-62214ffa07df",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
                "response.usage.prompt_tokens": 17,
                "response.usage.completion_tokens": 69,
                "response.usage.total_tokens": 86,
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "stop",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "a168214d-742d-4244-bd7f-62214ffa07df",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "meta.llama2-13b-chat-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "a168214d-742d-4244-bd7f-62214ffa07df",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "\n\n212°F = ?°C\n\nPlease help! I'm stuck!\n\nThank you!\n\nI hope this is the correct place to ask this question. Please let me know if it isn't.\n\nI appreciate your help!\n\nBest regards,\n\n[Your Name]",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "meta.llama2-13b-chat-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
}

chat_completion_streaming_expected_events = {
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "b427270f-371a-458d-81b6-a05aafb2704c",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
                "response.usage.completion_tokens": 35,
                "response.usage.total_tokens": 47,
                "response.usage.prompt_tokens": 12,
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "FINISH",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "b427270f-371a-458d-81b6-a05aafb2704c",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "b427270f-371a-458d-81b6-a05aafb2704c",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "\n1 degree Fahrenheit is 0.56 degrees Celsius. Therefore, 212 degree Fahrenheit in Celsius would be 115.72.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "anthropic.claude-instant-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "a645548f-0b3a-47ce-a675-f51e6e9037de",
                "duration": None,  # Response time varies each test run
                "request.model": "anthropic.claude-instant-v1",
                "response.model": "anthropic.claude-instant-v1",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "stop_sequence",
                "response.usage.completion_tokens": 99,
                "response.usage.prompt_tokens": 19,
                "response.usage.total_tokens": 118,
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "a645548f-0b3a-47ce-a675-f51e6e9037de",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "Human: What is 212 degrees Fahrenheit converted to Celsius? Assistant:",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "anthropic.claude-instant-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "a645548f-0b3a-47ce-a675-f51e6e9037de",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": " Here are the steps to convert 212 degrees Fahrenheit to Celsius:\n\n1) The formula to convert between Fahrenheit and Celsius is:\n   C = (F - 32) * 5/9\n\n2) Plug in 212 degrees Fahrenheit for F:\n   C = (212 - 32) * 5/9\n   C = 180 * 5/9\n   C = 100\n\n3) Therefore, 212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "anthropic.claude-instant-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "cohere.command-text-v14": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "4f8ab6c5-42d1-4e35-9573-30f9f41f821e",
                "response_id": None,  # UUID that varies with each run
                "duration": None,  # Response time varies each test run
                "request.model": "cohere.command-text-v14",
                "response.model": "cohere.command-text-v14",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "COMPLETE",
                "response.usage.completion_tokens": 91,
                "response.usage.total_tokens": 100,
                "response.usage.prompt_tokens": 9,
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "4f8ab6c5-42d1-4e35-9573-30f9f41f821e",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "4f8ab6c5-42d1-4e35-9573-30f9f41f821e",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": " To convert Fahrenheit to Celsius, you can use the formula:\n\nCelsius = (Fahrenheit - 32) * 5/9\n\nIn this case, if you have 212 degrees Fahrenheit, you can use this formula to calculate the equivalent temperature in Celsius:\n\nCelsius = (212 - 32) * 5/9 = 100 * 5/9 = 50\n\nTherefore, 212 degrees Fahrenheit is equivalent to 50 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "meta.llama2-13b-chat-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "6dd99878-0919-4f92-850c-48f50f923b76",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
                "response.usage.prompt_tokens": 17,
                "response.usage.completion_tokens": 100,
                "response.usage.total_tokens": 117,
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "length",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "6dd99878-0919-4f92-850c-48f50f923b76",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "meta.llama2-13b-chat-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "request_id": "6dd99878-0919-4f92-850c-48f50f923b76",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "content": "  What is the conversion formula?\n\n212 degrees Fahrenheit is equal to 100 degrees Celsius.\n\nThe conversion formula is:\n\n°C = (°F - 32) × 5/9\n\nSo, to convert 212 degrees Fahrenheit to Celsius, we can use the formula like this:\n\n°C = (212 - 32) × 5/9\n",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "meta.llama2-13b-chat-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
}

chat_completion_invalid_model_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.model": "does-not-exist",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]

chat_completion_invalid_access_key_error_events = {
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "15b39c8b-8e85-42c9-9623-06720301bda3",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "15b39c8b-8e85-42c9-9623-06720301bda3",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Invalid Token",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "ai21.j2-mid-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "9021791d-3797-493d-9277-e33aa6f6d544",
                "duration": None,  # Response time varies each test run
                "request.model": "ai21.j2-mid-v1",
                "response.model": "ai21.j2-mid-v1",
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
                "id": None,
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "9021791d-3797-493d-9277-e33aa6f6d544",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Invalid Token",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "ai21.j2-mid-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "anthropic.claude-instant-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "37396f55-b721-4bae-9461-4c369f5a080d",
                "duration": None,  # Response time varies each test run
                "request.model": "anthropic.claude-instant-v1",
                "response.model": "anthropic.claude-instant-v1",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "37396f55-b721-4bae-9461-4c369f5a080d",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Human: Invalid Token Assistant:",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "anthropic.claude-instant-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "cohere.command-text-v14": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "22476490-a0d6-42db-b5ea-32d0b8a7f751",
                "duration": None,  # Response time varies each test run
                "request.model": "cohere.command-text-v14",
                "response.model": "cohere.command-text-v14",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "22476490-a0d6-42db-b5ea-32d0b8a7f751",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Invalid Token",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "meta.llama2-13b-chat-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "22476490-a0d6-42db-b5ea-32d0b8a7f751",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "22476490-a0d6-42db-b5ea-32d0b8a7f751",
                "span_id": None,
                "trace_id": "trace-id",
                "transaction_id": "transaction-id",
                "content": "Invalid Token",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "meta.llama2-13b-chat-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
}


chat_completion_expected_malformed_request_body_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "e72d1b46-9f16-4bf0-8eee-f7778f32e5a5",
            "duration": None,  # Response time varies each test run
            "request.model": "amazon.titan-text-express-v1",
            "response.model": "amazon.titan-text-express-v1",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]

chat_completion_expected_malformed_response_body_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
            "duration": None,  # Response time varies each test run
            "request.model": "amazon.titan-text-express-v1",
            "response.model": "amazon.titan-text-express-v1",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Malformed Body",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "amazon.titan-text-express-v1",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]

chat_completion_expected_malformed_response_streaming_body_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "a5a8cebb-fd33-4437-8168-5667fbdfc1fb",
            "duration": None,  # Response time varies each test run
            "request.model": "amazon.titan-text-express-v1",
            "response.model": "amazon.titan-text-express-v1",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "a5a8cebb-fd33-4437-8168-5667fbdfc1fb",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Malformed Streaming Body",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "amazon.titan-text-express-v1",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]

chat_completion_expected_malformed_response_streaming_chunk_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "a5a8cebb-fd33-4437-8168-5667fbdfc1fb",
            "duration": None,  # Response time varies each test run
            "request.model": "amazon.titan-text-express-v1",
            "response.model": "amazon.titan-text-express-v1",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "a5a8cebb-fd33-4437-8168-5667fbdfc1fb",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Malformed Streaming Chunk",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "amazon.titan-text-express-v1",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]


chat_completion_expected_streaming_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "amazon.titan-text-express-v1",
            "response.model": "amazon.titan-text-express-v1",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Streaming Exception",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "amazon.titan-text-express-v1",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]
