chat_completion_payload_templates = {
    "amazon.titan-text-express-v1": '{ "inputText": "%s", "textGenerationConfig": {"temperature": %f, "maxTokenCount": %d }}',
    "ai21.j2-mid-v1": '{"prompt": "%s", "temperature": %f, "maxTokens": %d}',
}

chat_completion_expected_events = {
    "amazon.titan-text-express-v1": [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "api_key_last_four_digits": "CRET",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-text-express-v1",
                "response.usage.completion_tokens": 55,
                "response.usage.total_tokens": 67,
                "response.usage.prompt_tokens": 12,
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "FINISH",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "request.model": "amazon.titan-text-express-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "request_id": "660d4de9-6804-460e-8556-4ab2a019d1e3",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "\nUse the formula,\n°C = (°F - 32) x 5/9\n= 212 x 5/9\n= 100 degrees Celsius\n212 degrees Fahrenheit is 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "request.model": "amazon.titan-text-express-v1",
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
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "api_key_last_four_digits": "CRET",
                "duration": None,  # Response time varies each test run
                "request.model": "ai21.j2-mid-v1",
                "request.temperature": 0.7,
                "request.max_tokens": 100,
                "response.choices.finish_reason": "endoftext",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "number_of_messages": 2,
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "What is 212 degrees Fahrenheit converted to Celsius?",
                "role": "user",
                "completion_id": None,
                "sequence": 0,
                "request.model": "ai21.j2-mid-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
        (
            {"type": "LlmChatCompletionMessage"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_bedrock)",
                "conversation_id": "my-awesome-id",
                "request_id": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e",
                "span_id": "span-id",
                "trace_id": "trace-id",
                "transaction_id": None,
                "content": "\n212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                "role": "assistant",
                "completion_id": None,
                "sequence": 1,
                "request.model": "ai21.j2-mid-v1",
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
}
