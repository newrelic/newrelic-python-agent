embedding_payload_templates = {
    "amazon.titan-embed-text-v1": '{ "inputText": "%s" }',
    "amazon.titan-embed-g1-text-02": '{ "inputText": "%s" }',
}

embedding_expected_events = {
    "amazon.titan-embed-text-v1": [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (external_botocore)",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "api_key_last_four_digits": "CRET",
                "duration": None,  # Response time varies each test run
                "response.model": "amazon.titan-embed-text-v1",
                "request.model": "amazon.titan-embed-text-v1",
                "request_id": "75f1d3fe-6cde-4cf5-bdaf-7101f746ccfe",
                "response.usage.total_tokens": 6,
                "response.usage.prompt_tokens": 6,
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
    "amazon.titan-embed-g1-text-02": [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (external_botocore)",
                "transaction_id": None,
                "span_id": "span-id",
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "api_key_last_four_digits": "CRET",
                "duration": None,  # Response time varies each test run
                "response.model": "amazon.titan-embed-g1-text-02",
                "request.model": "amazon.titan-embed-g1-text-02",
                "request_id": "f7e78265-6b7c-4b3a-b750-0c1d00347258",
                "response.usage.total_tokens": 6,
                "response.usage.prompt_tokens": 6,
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ]
}
