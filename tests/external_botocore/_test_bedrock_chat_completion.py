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
    "mistral.mistral-7b-instruct-v0:2": '{"prompt": "<s>[INST] %s [/INST]", "temperature": %f, "max_tokens": %d}',
}

chat_completion_expected_events = {
    "mistral.mistral-7b-instruct-v0:2": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "duration": None,  # Response time varies each test run
                "request.model": "mistral.mistral-7b-instruct-v0:2",
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "<s>[INST] What is 212 degrees Fahrenheit converted to Celsius? [/INST]",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " To convert a temperature from Fahrenheit to Celsius, you can use the following formula:\n\nCelsius = (Fahrenheit - 32) \u00d7 5/9\n\nSo, to convert 212 degrees Fahrenheit to Celsius:\n\nCelsius = (212 - 32) \u00d7 5/9\nCelsius = 180.56 \u00d7 5/9\nCelsius",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "81508a1c-33a8-4294-8743-f0c629af2f49",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
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
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "a168214d-742d-4244-bd7f-62214ffa07df",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
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
chat_completion_langchain_expected_streaming_events = {
    "mistral.mistral-7b-instruct-v0:2": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "duration": None,  # Response time varies each test run
                "request.model": "mistral.mistral-7b-instruct-v0:2",
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "<s>[INST] What is 212 degrees Fahrenheit converted to Celsius? [/INST]",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " To convert a temperature from Fahrenheit to Celsius, you can use the following formula: Celsius = (Fahrenheit - 32) × 5/9.\n\nSo, to convert 212 degrees Fahrenheit to Celsius, do the following calculation:\n\nCelsius = (212°F - 32) × 5/9\n\nCelsius = (212 - 32)",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
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
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "\n\nUser: The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI:\n\nBot:",
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
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " Hello, how can I help you today?",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "duration": None,  # Response time varies each test run
                "request.model": "anthropic.claude-instant-v1",
                "response.model": "anthropic.claude-instant-v1",
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
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI:",
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
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "Hello! My name is Claude.\n\nH: Nice to meet you Claude. Can you tell me a bit about yourself?",
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
    "meta.llama2-13b-chat-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
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
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "[INST] The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI: [/INST]",
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
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "  Hello! It's great to talk to you! I'm an AI, and I'm here to help answer any questions you might have. What's on your mind? 🤔 Do you have a specific topic you'd like to discuss, or do you just want to chat? 💬 I'm all ears! 👂",
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
chat_completion_langchain_expected_events = {
    "mistral.mistral-7b-instruct-v0:2": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "duration": None,  # Response time varies each test run
                "request.model": "mistral.mistral-7b-instruct-v0:2",
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "<s>[INST] What is 212 degrees Fahrenheit converted to Celsius? [/INST]",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " To convert a temperature from Fahrenheit to Celsius, you can use the following formula:\n\nCelsius = (Fahrenheit - 32) \u00d7 5/9\n\nSo, to convert 212 degrees Fahrenheit to Celsius:\n\nCelsius = (212 - 32) \u00d7 5/9\nCelsius = 180.56 \u00d7 5/9\nCelsius",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
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
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "\n\nUser: The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI:\n\nBot:",
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
                "request_id": "884db5c9-18ab-4f27-8892-33656176a2e6",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " Hello, how can I help you today?",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "duration": None,  # Response time varies each test run
                "request.model": "anthropic.claude-instant-v1",
                "response.model": "anthropic.claude-instant-v1",
                "response.choices.finish_reason": "end_turn",
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
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI:",
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
                "request_id": "1a72a1f6-310f-469c-af1d-2c59eb600089",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "{'type': 'text', 'text': \"Hello! It's nice to meet you.\"}",
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
    "meta.llama2-13b-chat-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
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
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "[INST] The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\nHuman: Hi there!\nAI: [/INST]",
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
                "request_id": "cce6b34c-812c-4f97-8885-515829aa9639",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "  Hello! It's great to talk to you! I'm an AI, and I'm here to help answer any questions you might have. What's on your mind? 🤔 Do you have a specific topic you'd like to discuss, or is there something you'd like to know? 🤓 I'm all ears! 👂",
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
    "mistral.mistral-7b-instruct-v0:2": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "duration": None,  # Response time varies each test run
                "request.model": "mistral.mistral-7b-instruct-v0:2",
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "<s>[INST] What is 212 degrees Fahrenheit converted to Celsius? [/INST]",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": " To convert a temperature from Fahrenheit to Celsius, you can use the following formula: Celsius = (Fahrenheit - 32) × 5/9.\n\nSo, to convert 212 degrees Fahrenheit to Celsius, do the following calculation:\n\nCelsius = (212°F - 32) × 5/9\n\nCelsius = (212 - 32)",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "is_response": True,
            },
        ),
    ],
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "b427270f-371a-458d-81b6-a05aafb2704c",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
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
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "6dd99878-0919-4f92-850c-48f50f923b76",
                "duration": None,  # Response time varies each test run
                "request.model": "meta.llama2-13b-chat-v1",
                "response.model": "meta.llama2-13b-chat-v1",
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
    )
]

chat_completion_invalid_access_key_error_events = {
    "mistral.mistral-7b-instruct-v0:2": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "duration": None,  # Response time varies each test run
                "request.model": "mistral.mistral-7b-instruct-v0:2",
                "response.model": "mistral.mistral-7b-instruct-v0:2",
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
                "request_id": "48c7ee13-7790-461f-959f-04b0a4cf91c8",
                "span_id": None,
                "trace_id": "trace-id",
                "content": "<s>[INST] Invalid Token [/INST]",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "response.model": "mistral.mistral-7b-instruct-v0:2",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
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
    )
]

chat_completion_expected_malformed_response_body_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
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
