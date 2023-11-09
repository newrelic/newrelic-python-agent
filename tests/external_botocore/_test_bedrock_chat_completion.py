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
}

chat_completion_get_ai_message_ids = {
    "amazon.titan-text-express-v1": {
        "bedrock_key": [
            {
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "message_id": None,  # UUID that varies with each run
            },
            {
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "message_id": None,  # UUID that varies with each run
            },
        ]
    },
    "ai21.j2-mid-v1": {
        "bedrock_key": [
            {
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "message_id": "1234-0",
            },
            {
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "message_id": "1234-1",
            },
        ]
    },
    "anthropic.claude-instant-v1": {
        "bedrock_key": [
            {
                "conversation_id": "my-awesome-id",
                "request_id": "f354b9a7-9eac-4f50-a8d7-7d5d23566176",
                "message_id": None,  # UUID that varies with each run
            },
            {
                "conversation_id": "my-awesome-id",
                "request_id": "f354b9a7-9eac-4f50-a8d7-7d5d23566176",
                "message_id": None,  # UUID that varies with each run
            },
        ]
    },
    "cohere.command-text-v14": {
        "bedrock_key": [
            {
                "conversation_id": "my-awesome-id",
                "request_id": "c5188fb5-dc58-4cbe-948d-af173c69ce0d",
                "message_id": "a9cc8ce6-50b6-40b6-bf77-cf24561d8de7-0",
            },
            {
                "conversation_id": "my-awesome-id",
                "request_id": "c5188fb5-dc58-4cbe-948d-af173c69ce0d",
                "message_id": "a9cc8ce6-50b6-40b6-bf77-cf24561d8de7-1",
            },
        ]
    },
}

chat_completion_expected_events = {
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "api_key_last_four_digits": "CRET",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.model": "amazon.titan-text-express-v1",
                "response.usage.completion_tokens": 55,
                "response.usage.total_tokens": 67,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "\nUse the formula,\n°C = (°F - 32) x 5/9\n= 212 x 5/9\n= 100 degrees Celsius\n212 degrees Fahrenheit is 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "response_id": "1234",
                "api_key_last_four_digits": "CRET",
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "\n212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "f354b9a7-9eac-4f50-a8d7-7d5d23566176",
                "api_key_last_four_digits": "CRET",
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "f354b9a7-9eac-4f50-a8d7-7d5d23566176",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "f354b9a7-9eac-4f50-a8d7-7d5d23566176",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": " Here are the step-by-step workings:\n1) 212 degrees Fahrenheit \n2) To convert to Celsius, use the formula: C = (F - 32) * 5/9\n3) Plug in the values: C = (212 - 32) * 5/9 = 100 * 5/9 = 100 degrees Celsius\n\nSo, 212 degrees Fahrenheit converted to Celsius is",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "c5188fb5-dc58-4cbe-948d-af173c69ce0d",
                "response_id": None,  # UUID that varies with each run
                "api_key_last_four_digits": "CRET",
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "c5188fb5-dc58-4cbe-948d-af173c69ce0d",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
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
                "appName": "Python Agent Test (external_botocore)",
                "conversation_id": "my-awesome-id",
                "request_id": "c5188fb5-dc58-4cbe-948d-af173c69ce0d",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": " To convert 212 degrees Fahrenheit to Celsius, we can use the conversion factor that Celsius is equal to (Fahrenheit - 32) x 5/9. \\n\\nApplying this formula, we have:\\n212Â°F = (212Â°F - 32) x 5/9\\n= (180) x 5/9\\n= 100Â°C.\\n\\nTherefore, 212 degrees F",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "response.model": "cohere.command-text-v14",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
}
