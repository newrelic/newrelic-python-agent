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

import google.genai
import pytest
from google.genai import types
from testing_support.fixtures import override_llm_token_callback_settings, reset_core_stats_engine
from testing_support.ml_testing_utils import llm_token_count_callback, set_trace_info
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.background_task import background_task


def _thinking_response():
    # candidates_token_count does not include the thoughts tokens, but total_token_count does.
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text="Six.")]), finish_reason="STOP")
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=18, candidates_token_count=2, thoughts_token_count=40, total_token_count=60
        ),
        model_version="gemini-3.5-flash",
    )


@pytest.fixture
def thinking_model(monkeypatch):
    monkeypatch.setattr(google.genai.models.Models, "_generate_content", lambda self, **kwargs: _thinking_response())


def _summary_event(**usage):
    return [
        (
            {"type": "LlmChatCompletionSummary"},
            {
                "id": None,
                "timestamp": None,
                "span_id": None,
                "trace_id": "trace-id",
                "duration": None,
                "request.model": "gemini-3.5-flash",
                "response.model": "gemini-3.5-flash",
                "response.choices.finish_reason": "STOP",
                "vendor": "gemini",
                "ingest_source": "Python",
                "response.number_of_messages": 2,
                **usage,
            },
        )
    ]


@reset_core_stats_engine()
@validate_custom_events(
    _summary_event(
        **{"response.usage.prompt_tokens": 18, "response.usage.completion_tokens": 2, "response.usage.total_tokens": 60}
    )
)
@background_task()
def test_total_tokens_includes_thoughts_tokens(gemini_client, thinking_model, set_trace_info):
    set_trace_info()
    gemini_client.models.generate_content(model="gemini-3.5-flash", contents="How many letters are in Python?")


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(
    _summary_event(
        **{
            "response.usage.prompt_tokens": 105,
            "response.usage.completion_tokens": 105,
            "response.usage.total_tokens": 210,
        }
    )
)
@background_task()
def test_total_tokens_follow_the_token_count_callback(gemini_client, thinking_model, set_trace_info):
    set_trace_info()
    gemini_client.models.generate_content(model="gemini-3.5-flash", contents="How many letters are in Python?")
