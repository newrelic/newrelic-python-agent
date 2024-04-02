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

import asyncio
import uuid

import langchain
import openai
import pytest
from langchain.chains.openai_functions import (
    create_structured_output_chain,
    create_structured_output_runnable,
)
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseOutputParser
from mock import patch
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
)
from testing_support.ml_testing_utils import (  # noqa: F401
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_sans_content,
    set_trace_info,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_transaction_error_event_count import (
    validate_transaction_error_event_count,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)


chat_completion_recorded_events_invoke_langchain_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 1,
            "metadata.id": "123",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'no-exist': 'Sally is 13'}",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events_runnable_invoke_openai_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 1,
            "metadata.id": "123",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'input': 'Sally is 13'}",
            "completion_id": None,
            "sequence": 0,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
        },
    ),
]
chat_completion_recorded_events_runnable_invoke = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 2,
            "metadata.id": "123",
            "tags": "['bar']",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'input': 'Sally is 13'}",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'name': 'Sally', 'age': 13}",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]
chat_completion_recorded_events_invoke = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 2,
            "metadata.id": "123",
            "tags": "['bar']",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'input': 'Sally is 13'}",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'function': {'name': 'Sally', 'age': 13}}",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]
chat_completion_recorded_events_runnable_invoke_no_metadata_or_tags = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 2,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'input': 'Sally is 13'}",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'name': 'Sally', 'age': 13}",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]
chat_completion_recorded_events_invoke_no_metadata_or_tags = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 2,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'input': 'Sally is 13'}",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'function': {'name': 'Sally', 'age': 13}}",
            "completion_id": None,
            "sequence": 1,
            "vendor": "langchain",
            "ingest_source": "Python",
            "is_response": True,
            "virtual_llm": True,
        },
    ),
]

chat_completion_recorded_events_list_response = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 2,
            "metadata.id": "123",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "{'text': 'colors'}",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": None,
            "duration": None,
            "response.number_of_messages": 1,
            "metadata.id": "123",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
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
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
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
@validate_custom_events(chat_completion_recorded_events_list_response)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_langchain_chain_list_response",
    scoped_metrics=[("Llm/chain/Langchain/invoke", 1)],
    rollup_metrics=[("Llm/chain/Langchain/invoke", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_chain_list_response(set_trace_info, comma_separated_list_output_parser, chat_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

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
    chain.invoke(
        {"text": "colors"},
        config={"metadata": {"id": "123"}},
    )


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
            },
            chat_completion_recorded_events_runnable_invoke,
            id="runnable_chain.invoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
            },
            chat_completion_recorded_events_runnable_invoke,
            id="runnable_chain.invoke-with-only-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"input": "Sally is 13"},),
            {},
            chat_completion_recorded_events_runnable_invoke_no_metadata_or_tags,
            id="runnable_chain.invoke-with-only-args",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke,
            id="chain.invoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke,
            id="chain.invoke-with-only-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke_no_metadata_or_tags,
            id="chain.invoke-with-only-args",
        ),
    ),
)
def test_langchain_chain(
    set_trace_info,
    json_schema,
    prompt,
    chat_openai_client,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
):
    @reset_core_stats_engine()
    @validate_custom_events(expected_events)
    # 3 langchain events and 5 openai events.
    @validate_custom_event_count(count=8)
    @validate_transaction_metrics(
        name="test_chain:test_langchain_chain.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        output = getattr(runnable, call_function)(*call_function_args, **call_function_kwargs)

        assert output

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
            },
            events_sans_content(chat_completion_recorded_events_runnable_invoke),
            id="runnable_chain.invoke",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            events_sans_content(chat_completion_recorded_events_invoke),
            id="chain.invoke",
        ),
    ),
)
def test_langchain_chain_no_content(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
):
    @reset_core_stats_engine()
    @disabled_ai_monitoring_record_content_settings
    @validate_custom_events(expected_events)
    # 3 langchain events and 5 openai events.
    @validate_custom_event_count(count=8)
    @validate_transaction_metrics(
        name="test_chain:test_langchain_chain_no_content.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        output = getattr(runnable, call_function)(*call_function_args, **call_function_kwargs)

        assert output

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="runnable_chain.invoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "metadata": {"id": "123"},
                },
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="runnable_chain.invoke-only-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="chain.run-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="chain.invoke-only-kwargs",
        ),
    ),
)
def test_langchain_chain_error_in_openai(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt_openai_error,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
):
    @reset_core_stats_engine()
    @validate_transaction_error_event_count(1)
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=6)
    @validate_transaction_metrics(
        name="test_chain:test_langchain_chain_error_in_openai.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt_openai_error)

        with pytest.raises(openai.AuthenticationError):
            getattr(runnable, call_function)(*call_function_args, **call_function_kwargs)

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events,expected_error",
    (
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_invoke_langchain_error,
            KeyError,
            id="runnable_chain.invoke",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke_langchain_error,
            ValueError,
            id="chain.invoke",
        ),
    ),
)
def test_langchain_chain_error_in_langchain(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    expected_error,
):
    @reset_core_stats_engine()
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(
        callable_name(expected_error),
    )
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_chain:test_langchain_chain_error_in_langchain.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        with pytest.raises(expected_error):
            getattr(runnable, call_function)(*call_function_args, **call_function_kwargs)

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events,expected_error",
    (
        pytest.param(
            create_structured_output_runnable,
            "invoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                }
            },
            events_sans_content(chat_completion_recorded_events_invoke_langchain_error),
            KeyError,
            id="runnable_chain.invoke",
        ),
        pytest.param(
            create_structured_output_chain,
            "invoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            events_sans_content(chat_completion_recorded_events_invoke_langchain_error),
            ValueError,
            id="chain.invoke",
        ),
    ),
)
def test_langchain_chain_error_in_langchain_no_content(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    expected_error,
):
    @reset_core_stats_engine()
    @disabled_ai_monitoring_record_content_settings
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(
        callable_name(expected_error),
    )
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_chain:test_langchain_chain_error_in_langchain_no_content.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        with pytest.raises(expected_error):
            getattr(runnable, call_function)(*call_function_args, **call_function_kwargs)

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,input_",
    ((create_structured_output_runnable, "invoke", {"input": "Sally is 13"}),),
)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_langchain_chain_outside_transaction(
    set_trace_info, chat_openai_client, json_schema, prompt, create_function, call_function, input_
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    runnable = create_function(json_schema, chat_openai_client, prompt)

    output = getattr(runnable, call_function)(input_)

    assert output == {"name": "Sally", "age": 13}


@disabled_ai_monitoring_settings
@pytest.mark.parametrize(
    "create_function,call_function,input_",
    ((create_structured_output_runnable, "invoke", {"input": "Sally is 13"}),),
)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_langchain_chain_ai_monitoring_disabled(
    set_trace_info, chat_openai_client, json_schema, prompt, create_function, call_function, input_
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    runnable = create_function(json_schema, chat_openai_client, prompt)

    output = getattr(runnable, call_function)(input_)

    assert output == {"name": "Sally", "age": 13}


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_list_response)
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_list_response",
    scoped_metrics=[("Llm/chain/Langchain/ainvoke", 1)],
    rollup_metrics=[("Llm/chain/Langchain/ainvoke", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_list_response(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

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
        chain.ainvoke(
            {"text": "colors"},
            config={
                "metadata": {"id": "123"},
            },
        )
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(chat_completion_recorded_events_list_response))
@validate_custom_event_count(count=7)
@validate_transaction_metrics(
    name="test_chain:test_async_langchain_chain_list_response_no_content",
    scoped_metrics=[("Llm/chain/Langchain/ainvoke", 1)],
    rollup_metrics=[("Llm/chain/Langchain/ainvoke", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_langchain_chain_list_response_no_content(
    set_trace_info, comma_separated_list_output_parser, chat_openai_client, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

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
        chain.ainvoke(
            {"text": "colors"},
            config={
                "metadata": {"id": "123"},
            },
        )
    )


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_runnable_invoke,
            id="runnable_chain.ainvoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
            },
            chat_completion_recorded_events_runnable_invoke,
            id="runnable_chain.ainvoke-with-only-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {},
            chat_completion_recorded_events_runnable_invoke_no_metadata_or_tags,
            id="runnable_chain.ainvoke-with-only-args",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke,
            id="chain.ainvoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke,
            id="chain.ainvoke-with-only-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke_no_metadata_or_tags,
            id="chain.ainvoke-with-only-args",
        ),
    ),
)
def test_async_langchain_chain(
    set_trace_info,
    json_schema,
    prompt,
    chat_openai_client,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    loop,
):
    @reset_core_stats_engine()
    @validate_custom_events(expected_events)
    # 3 langchain events and 5 openai events.
    @validate_custom_event_count(count=8)
    @validate_transaction_metrics(
        name="test_chain:test_async_langchain_chain.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        loop.run_until_complete(getattr(runnable, call_function)(*call_function_args, **call_function_kwargs))

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="runnable_chain.ainvoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "metadata": {"id": "123"},
                },
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="runnable_chain.ainvoke-only-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": [],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="chain.arun-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            (),
            {
                "input": {"input": "Sally is 13"},
                "config": {
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_runnable_invoke_openai_error,
            id="chain.arun-only-kwargs",
        ),
    ),
)
def test_async_langchain_chain_error_in_openai(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt_openai_error,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    loop,
):
    @reset_core_stats_engine()
    @validate_transaction_error_event_count(1)
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=6)
    @validate_transaction_metrics(
        name="test_chain:test_async_langchain_chain_error_in_openai.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt_openai_error)

        with pytest.raises(openai.AuthenticationError):
            loop.run_until_complete(getattr(runnable, call_function)(*call_function_args, **call_function_kwargs))

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events,expected_error",
    (
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_invoke_langchain_error,
            KeyError,
            id="runnable_chain.ainvoke",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke_langchain_error,
            ValueError,
            id="chain.ainvoke",
        ),
    ),
)
def test_async_langchain_chain_error_in_langchain(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    expected_error,
    loop,
):
    @reset_core_stats_engine()
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(
        callable_name(expected_error),
    )
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_chain:test_async_langchain_chain_error_in_langchain.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        with pytest.raises(expected_error):
            loop.run_until_complete(getattr(runnable, call_function)(*call_function_args, **call_function_kwargs))

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events,expected_error",
    (
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "metadata": {"id": "123"},
                }
            },
            events_sans_content(chat_completion_recorded_events_invoke_langchain_error),
            KeyError,
            id="runnable_chain.ainvoke",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"no-exist": "Sally is 13"},),
            {
                "config": {
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            events_sans_content(chat_completion_recorded_events_invoke_langchain_error),
            ValueError,
            id="chain.ainvoke",
        ),
    ),
)
def test_async_langchain_chain_error_in_langchain_no_content(
    set_trace_info,
    chat_openai_client,
    json_schema,
    prompt,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    expected_error,
    loop,
):
    @reset_core_stats_engine()
    @disabled_ai_monitoring_record_content_settings
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(
        callable_name(expected_error),
    )
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_chain:test_async_langchain_chain_error_in_langchain_no_content.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        runnable = create_function(json_schema, chat_openai_client, prompt)

        with pytest.raises(expected_error):
            loop.run_until_complete(getattr(runnable, call_function)(*call_function_args, **call_function_kwargs))

    _test()


@pytest.mark.parametrize(
    "create_function,call_function,input_",
    (
        (create_structured_output_runnable, "ainvoke", {"input": "Sally is 13"}),
        (create_structured_output_chain, "arun", "Sally is 13"),
    ),
)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_async_langchain_chain_outside_transaction(
    set_trace_info, chat_openai_client, json_schema, prompt, create_function, call_function, input_, loop
):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    runnable = create_function(json_schema, chat_openai_client, prompt)

    loop.run_until_complete(getattr(runnable, call_function)(input_))


@pytest.mark.parametrize(
    "create_function,call_function,call_function_args,call_function_kwargs,expected_events",
    (
        pytest.param(
            create_structured_output_runnable,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                }
            },
            chat_completion_recorded_events_runnable_invoke,
            id="runnable_chain.ainvoke-with-args-and-kwargs",
        ),
        pytest.param(
            create_structured_output_chain,
            "ainvoke",
            ({"input": "Sally is 13"},),
            {
                "config": {
                    "tags": ["bar"],
                    "metadata": {"id": "123"},
                },
                "return_only_outputs": True,
            },
            chat_completion_recorded_events_invoke,
            id="chain.ainvoke-with-args-and-kwargs",
        ),
    ),
)
def test_multiple_async_langchain_chain(
    set_trace_info,
    json_schema,
    prompt,
    chat_openai_client,
    create_function,
    call_function,
    call_function_args,
    call_function_kwargs,
    expected_events,
    loop,
):
    call1 = expected_events.copy()
    call1[0][1]["request_id"] = "b1883d9d-10d6-4b67-a911-f72849704e92"
    call1[1][1]["request_id"] = "b1883d9d-10d6-4b67-a911-f72849704e92"
    call1[2][1]["request_id"] = "b1883d9d-10d6-4b67-a911-f72849704e92"
    call2 = expected_events.copy()
    call2[0][1]["request_id"] = "a58aa0c0-c854-4657-9e7b-4cce442f3b61"
    call2[1][1]["request_id"] = "a58aa0c0-c854-4657-9e7b-4cce442f3b61"
    call2[2][1]["request_id"] = "a58aa0c0-c854-4657-9e7b-4cce442f3b61"

    @reset_core_stats_engine()
    @validate_custom_events(call1 + call2)
    # 3 langchain events and 5 openai events.
    @validate_custom_event_count(count=16)
    @validate_transaction_metrics(
        name="test_chain:test_multiple_async_langchain_chain.<locals>._test",
        scoped_metrics=[("Llm/chain/Langchain/%s" % call_function, 2)],
        rollup_metrics=[("Llm/chain/Langchain/%s" % call_function, 2)],
        custom_metrics=[
            ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
        ],
        background_task=True,
    )
    @background_task()
    def _test():
        with patch("langchain_core.callbacks.manager.uuid", autospec=True) as mock_uuid:
            mock_uuid.uuid4.side_effect = [
                uuid.UUID("b1883d9d-10d6-4b67-a911-f72849704e92"),  # first call
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b61"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b61"),  # second call
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b63"),
                uuid.UUID("b1883d9d-10d6-4b67-a911-f72849704e93"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b64"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b65"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b66"),
            ]
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            runnable = create_function(json_schema, chat_openai_client, prompt)

            call1 = asyncio.ensure_future(
                getattr(runnable, call_function)(*call_function_args, **call_function_kwargs), loop=loop
            )
            call2 = asyncio.ensure_future(
                getattr(runnable, call_function)(*call_function_args, **call_function_kwargs), loop=loop
            )
            loop.run_until_complete(asyncio.gather(call1, call2))

    _test()


@pytest.fixture
def json_schema():
    return {
        "title": "Person",
        "description": "Identifying information about a person.",
        "type": "object",
        "properties": {
            "name": {"title": "Name", "description": "The person's name", "type": "string"},
            "age": {"title": "Age", "description": "The person's age", "type": "integer"},
            "fav_food": {
                "title": "Fav Food",
                "description": "The person's favorite food",
                "type": "string",
            },
        },
        "required": ["name", "age"],
    }


@pytest.fixture
def prompt():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a world class algorithm for extracting information in structured formats.",
            ),
            (
                "human",
                "Use the given format to extract information from the following input: {input}",
            ),
            ("human", "Tip: Make sure to answer in the correct format"),
        ]
    )


@pytest.fixture
def prompt_openai_error():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a world class algorithm for extracting information in structured formats with openai failures.",
            ),
            (
                "human",
                "Use the given format to extract information from the following input: {input}",
            ),
            ("human", "Tip: Make sure to answer in the correct format"),
        ]
    )


@pytest.fixture
def comma_separated_list_output_parser():
    class _CommaSeparatedListOutputParser(BaseOutputParser):
        """Parse the output of an LLM call to a comma-separated list."""

        def parse(self, text):
            """Parse the output of an LLM call."""
            return text.strip().split(", ")

    return _CommaSeparatedListOutputParser()
