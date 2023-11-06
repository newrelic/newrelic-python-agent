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

from mlmodel_bedrock.test_chat_completion import (  # noqa: F401; pylint: disable=W0611
    exercise_model,
    is_file_payload,
    model_id,
)
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import get_ai_message_ids
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import add_custom_attribute, current_transaction

_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


def set_trace_info():
    txn = current_transaction()
    if txn:
        txn._trace_id = "trace-id"
    trace = current_trace()
    if trace:
        trace.guid = "span-id"


@reset_core_stats_engine()
@background_task()
def test_get_ai_message_ids_when_nr_message_ids_not_set():
    message_ids = get_ai_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
def test_get_ai_message_ids_outside_transaction():
    message_ids = get_ai_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
def test_get_ai_message_ids_bedrock_chat_completion_in_txn(exercise_model):  # noqa: F811
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)
        message_ids = [m for m in get_ai_message_ids()]

        for message_id_info in message_ids:
            # Check to see if this equals the conversation ID we added
            assert message_id_info["conversation_id"] == "my-awesome-id"
            # Check to see if this exists
            assert message_id_info["message_id"]

    _test()
