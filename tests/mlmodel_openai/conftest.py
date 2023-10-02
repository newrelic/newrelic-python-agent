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

import pytest
from openai.util import convert_to_openai_object
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ml_insights_event.enabled": True,
}
collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_openai)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_openai)"],
)


@pytest.fixture(autouse=True)
def openai_chat_completion_dict():
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {"content": "212 degrees Fahrenheit is 100 degrees Celsius.", "role": "assistant"},
            }
        ],
        "created": 1676917710,
        "id": "some-test-id-123456789",
        "model": "gpt-3.5-turbo-0613",
        "object": "chat.completion",
        "usage": {"completion_tokens": 7, "prompt_tokens": 3, "total_tokens": 10},
    }


@pytest.fixture(autouse=True)
def openai_embedding_dict():
    return {
        "data": [
            {
                "embedding": [
                    -0.006929283495992422,
                    -0.005336422007530928,
                ],
                "index": 0,
                "object": "embedding",
            }
        ],
        "model": "text-embedding-ada-002",
        "object": "list",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }


@pytest.fixture(autouse=True)
def openai_chat_completion_object(openai_chat_completion_dict):
    return convert_to_openai_object(openai_chat_completion_dict)


@pytest.fixture(autouse=True)
def openai_embedding_object(openai_embedding_dict):
    return convert_to_openai_object(openai_embedding_dict)
