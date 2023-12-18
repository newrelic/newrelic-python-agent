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

import openai
from langchain.chains.openai_functions.openapi import get_openapi_chain
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute

disabled_custom_insights_settings = {"custom_insights_events.enabled": False}

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

chat_completion_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.model": "gpt-3.5-turbo-0613",
            "response.organization": "new-relic-nkmd8b",
            "response.usage.completion_tokens": 11,
            "response.usage.total_tokens": 64,
            "response.usage.prompt_tokens": 53,
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "stop",
            "response.api_type": "None",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 40000,
            "response.headers.ratelimitResetTokens": "90ms",
            "response.headers.ratelimitResetRequests": "7m12s",
            "response.headers.ratelimitRemainingTokens": 39940,
            "response.headers.ratelimitRemainingRequests": 199,
            "response.headers.ratelimitLimitTokensUsageBased": "",
            "response.headers.ratelimitResetTokensUsageBased": "",
            "response.headers.ratelimitRemainingTokensUsageBased": "",
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-0",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-1",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-2",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain(set_trace_info):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")

    chain = get_openapi_chain("https://www.klarna.com/us/shopping/public/openai/v0/api-docs/")
    chain.run("What are some options for a men's large blue button down shirt")
