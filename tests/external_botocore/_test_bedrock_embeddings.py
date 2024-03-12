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
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "duration": None,  # Response time varies each test run
                "response.model": "amazon.titan-embed-text-v1",
                "request.model": "amazon.titan-embed-text-v1",
                "request_id": "11233989-07e8-4ecb-9ba6-79601ba6d8cc",
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
                "transaction_id": "transaction-id",
                "llm.conversation_id": "my-awesome-id",
                "llm.foo": "bar",
                "span_id": None,
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "duration": None,  # Response time varies each test run
                "response.model": "amazon.titan-embed-g1-text-02",
                "request.model": "amazon.titan-embed-g1-text-02",
                "request_id": "b10ac895-eae3-4f07-b926-10b2866c55ed",
                "response.usage.total_tokens": 6,
                "response.usage.prompt_tokens": 6,
                "vendor": "bedrock",
                "ingest_source": "Python",
            },
        ),
    ],
}

embedding_expected_error_events = {
    "amazon.titan-embed-text-v1": [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "input": "Invalid Token",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-embed-text-v1",
                "response.model": "amazon.titan-embed-text-v1",
                "request_id": "aece6ad7-e2ff-443b-a953-ba7d385fd0cc",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "error": True,
            },
        ),
    ],
    "amazon.titan-embed-g1-text-02": [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "transaction_id": "transaction-id",
                "span_id": None,
                "trace_id": "trace-id",
                "input": "Invalid Token",
                "duration": None,  # Response time varies each test run
                "request.model": "amazon.titan-embed-g1-text-02",
                "response.model": "amazon.titan-embed-g1-text-02",
                "request_id": "73328313-506e-4da8-af0f-51017fa6ca3f",
                "vendor": "bedrock",
                "ingest_source": "Python",
                "error": True,
            },
        ),
    ],
}

embedding_expected_client_errors = {
    "amazon.titan-embed-text-v1": {
        "http.statusCode": 403,
        "error.message": "The security token included in the request is invalid.",
        "error.code": "UnrecognizedClientException",
    },
    "amazon.titan-embed-g1-text-02": {
        "http.statusCode": 403,
        "error.message": "The security token included in the request is invalid.",
        "error.code": "UnrecognizedClientException",
    },
}
