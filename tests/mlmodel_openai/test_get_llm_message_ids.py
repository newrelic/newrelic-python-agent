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
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_custom_event_count,
)

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import get_llm_message_ids, record_llm_feedback_event
from newrelic.api.transaction import add_custom_attribute, current_transaction

_test_openai_chat_completion_messages_1 = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)
_test_openai_chat_completion_messages_2 = (
    {"role": "system", "content": "You are a mathematician."},
    {"role": "user", "content": "What is 1 plus 2?"},
)
expected_message_ids_1 = [
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-0",
    },
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-1",
    },
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-2",
    },
]

expected_message_ids_1_no_conversation_id = [
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-0",
    },
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-1",
    },
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059ccd",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv-2",
    },
]
expected_message_ids_2 = [
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-0",
    },
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-1",
    },
    {
        "conversation_id": "my-awesome-id",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-2",
    },
]
expected_message_ids_2_no_conversation_id = [
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-0",
    },
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-1",
    },
    {
        "conversation_id": "",
        "request_id": "49dbbffbd3c3f4612aa48def69059aad",
        "message_id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat-2",
    },
]


@reset_core_stats_engine()
@background_task()
def test_get_llm_message_ids_when_nr_message_ids_not_set():
    message_ids = get_llm_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
def test_get_llm_message_ids_outside_transaction():
    message_ids = get_llm_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
@background_task()
def test_get_llm_message_ids_mulitple_async(loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    async def _run():
        res1 = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_1, temperature=0.7, max_tokens=100
        )
        res2 = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_2, temperature=0.7, max_tokens=100
        )
        return [res1, res2]

    results = loop.run_until_complete(_run())

    message_ids = [m for m in get_llm_message_ids(results[0].id)]
    assert message_ids == expected_message_ids_1

    message_ids = [m for m in get_llm_message_ids(results[1].id)]
    assert message_ids == expected_message_ids_2

    # Make sure we aren't causing a memory leak.
    transaction = current_transaction()
    assert not transaction._nr_message_ids


@reset_core_stats_engine()
@background_task()
def test_get_llm_message_ids_mulitple_async_no_conversation_id(loop, set_trace_info):
    set_trace_info()

    async def _run():
        res1 = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_1, temperature=0.7, max_tokens=100
        )
        res2 = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_2, temperature=0.7, max_tokens=100
        )
        return [res1, res2]

    results = loop.run_until_complete(_run())

    message_ids = [m for m in get_llm_message_ids(results[0].id)]
    assert message_ids == expected_message_ids_1_no_conversation_id

    message_ids = [m for m in get_llm_message_ids(results[1].id)]
    assert message_ids == expected_message_ids_2_no_conversation_id

    # Make sure we aren't causing a memory leak.
    transaction = current_transaction()
    assert not transaction._nr_message_ids


@reset_core_stats_engine()
# Three chat completion messages and one chat completion summary for each create call (8 in total)
# Three feedback events for the first create call
@validate_custom_event_count(11)
@background_task()
def test_get_llm_message_ids_mulitple_sync(set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    results = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_1, temperature=0.7, max_tokens=100
    )
    message_ids = [m for m in get_llm_message_ids(results.id)]
    assert message_ids == expected_message_ids_1

    for message_id in message_ids:
        record_llm_feedback_event(
            category="informative",
            rating=1,
            message_id=message_id.get("message_id"),
            request_id=message_id.get("request_id"),
            conversation_id=message_id.get("conversation_id"),
        )

    results = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_2, temperature=0.7, max_tokens=100
    )
    message_ids = [m for m in get_llm_message_ids(results.id)]
    assert message_ids == expected_message_ids_2

    # Make sure we aren't causing a memory leak.
    transaction = current_transaction()
    assert not transaction._nr_message_ids


@reset_core_stats_engine()
@validate_custom_event_count(11)
@background_task()
def test_get_llm_message_ids_mulitple_sync_no_conversation_id(set_trace_info):
    set_trace_info()

    results = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_1, temperature=0.7, max_tokens=100
    )
    message_ids = [m for m in get_llm_message_ids(results.id)]
    assert message_ids == expected_message_ids_1_no_conversation_id

    for message_id in message_ids:
        record_llm_feedback_event(
            category="informative",
            rating=1,
            message_id=message_id.get("message_id"),
            request_id=message_id.get("request_id"),
            conversation_id=message_id.get("conversation_id"),
        )

    results = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages_2, temperature=0.7, max_tokens=100
    )
    message_ids = [m for m in get_llm_message_ids(results.id)]
    assert message_ids == expected_message_ids_2_no_conversation_id

    # Make sure we aren't causing a memory leak.
    transaction = current_transaction()
    assert not transaction._nr_message_ids
