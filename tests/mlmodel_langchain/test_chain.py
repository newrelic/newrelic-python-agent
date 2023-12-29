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

import langchain
import openai
import pytest
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseOutputParser
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_custom_event_count,
    validate_transaction_error_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

disabled_custom_insights_settings = {"custom_insights_events.enabled": False}

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)
chat_completion_recorded_events_uuid_message_ids = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 6,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "colors",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "red",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events_missing_conversation_id = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 6,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "message-id-0",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "colors",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "message-id-1",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "red",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 6,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "message-id-0",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "colors",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "message-id-1",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "red",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events_error_in_openai = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 1,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "openai failure",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events_error_in_langchain = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 1,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_langchain)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "colors",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser
    chain.invoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_missing_conversation_id)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain_without_conversation_id",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain_without_conversation_id(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client
):
    set_trace_info()

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser
    chain.invoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_uuid_message_ids)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain_without_message_ids",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain_without_message_ids(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser
    chain.invoke({"text": "colors"})


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_custom_events(chat_completion_recorded_events_error_in_openai)
@validate_custom_event_count(count=5)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain_error_in_openai",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain_error_in_openai(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 4 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    with pytest.raises(openai.AuthenticationError):
        chain.invoke({"text": "openai failure"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(AttributeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_custom_events(chat_completion_recorded_events_error_in_langchain)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain_error_in_lanchain",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain_error_in_lanchain(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    with pytest.raises(AttributeError):
        chain.invoke({"text": "colors"}, config=[])


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_langchain_chain_outside_transaction(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    chain.invoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain(set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    loop.run_until_complete(
        chain.ainvoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})
    )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_missing_conversation_id)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_without_conversation_id",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_without_conversation_id(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    loop.run_until_complete(
        chain.ainvoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})
    )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_uuid_message_ids)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_without_message_ids",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_without_message_ids(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    loop.run_until_complete(chain.ainvoke({"text": "colors"}))


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_custom_events(chat_completion_recorded_events_error_in_openai)
@validate_custom_event_count(count=5)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_error_in_openai",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_error_in_openai(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 4 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    with pytest.raises(openai.AuthenticationError):
        loop.run_until_complete(
            chain.ainvoke(
                {"text": "openai failure"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}}
            )
        )


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(AttributeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_custom_events(chat_completion_recorded_events_error_in_langchain)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_error_in_lanchain",
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_error_in_lanchain(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    with pytest.raises(AttributeError):
        loop.run_until_complete(chain.ainvoke({"text": "colors"}, config=[]))


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_async_langchain_chain_outside_transaction(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    template = """You are a helpful assistant who generates comma separated lists.
    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.
    ONLY return a comma separated list, and nothing more."""
    human_template = "{text}"

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", human_template),
        ]
    )
    chain = chat_prompt | chat_openai_client | comma_separated_list_output_parser

    loop.run_until_complete(
        chain.ainvoke({"text": "colors"}, config={"metadata": {"message_ids": ["message-id-0", "message-id-1"]}})
    )


@pytest.fixture
def comma_separated_list_output_parser():
    class _CommaSeparatedListOutputParser(BaseOutputParser):
        """Parse the output of an LLM call to a comma-separated list."""

        def parse(self, text):
            """Parse the output of an LLM call."""
            return text.strip().split(", ")

    return _CommaSeparatedListOutputParser()
