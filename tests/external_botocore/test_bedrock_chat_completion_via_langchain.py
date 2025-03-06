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
from _test_bedrock_chat_completion import (
    chat_completion_langchain_expected_events,
    chat_completion_langchain_expected_streaming_events,
)
from conftest import BOTOCORE_VERSION  # pylint: disable=E0611
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import events_with_context_attrs, set_trace_info
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute

UNSUPPORTED_LANGCHAIN_MODELS = ["ai21.j2-mid-v1", "cohere.command-text-v14"]


@pytest.fixture(
    scope="module",
    params=[
        "amazon.titan-text-express-v1",
        "ai21.j2-mid-v1",
        "anthropic.claude-instant-v1",
        "cohere.command-text-v14",
        "meta.llama2-13b-chat-v1",
    ],
)
def model_id(request):
    model = request.param
    if model in UNSUPPORTED_LANGCHAIN_MODELS:
        pytest.skip(reason="Not supported by Langchain.")
    return model


@pytest.fixture(scope="session", params=[False, True], ids=["ResponseStandard", "ResponseStreaming"])
def response_streaming(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, response_streaming):
    try:
        # These are only available in certain botocore environments.
        from langchain.chains import ConversationChain
        from langchain_community.chat_models import BedrockChat
    except ImportError:
        pytest.skip(reason="Langchain not installed.")

    def _exercise_model(prompt):
        bedrock_llm = BedrockChat(model_id=model_id, client=bedrock_server, streaming=response_streaming)
        conversation = ConversationChain(llm=bedrock_llm)
        result = conversation.predict(input=prompt)
        if response_streaming:
            for r in result:
                assert r
        else:
            assert result

    return _exercise_model


@pytest.fixture(scope="module")
def expected_events(model_id, response_streaming):
    if response_streaming:
        return chat_completion_langchain_expected_streaming_events[model_id]
    return chat_completion_langchain_expected_events[model_id]


@pytest.fixture(scope="module")
def expected_metrics(response_streaming):
    if response_streaming:
        return [("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)]
    return [("Llm/completion/Bedrock/invoke_model", 1)]


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_llm_metadata(
    set_trace_info, exercise_model, expected_events, expected_metrics, response_streaming
):
    @validate_custom_events(events_with_context_attrs(expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=6)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_llm_metadata",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_in_txn_with_llm_metadata")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        with WithLlmCustomAttributes({"context": "attr"}):
            exercise_model(prompt="Hi there!")

    _test()
