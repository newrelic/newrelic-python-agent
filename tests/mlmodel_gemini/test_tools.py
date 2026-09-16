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

import sys

import google.genai
import pytest
from conftest import GEMINI_VERSION_METRIC
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings, set_trace_info
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute

PROMPT = "What is the capital of France?"
EXPECTED_TOOL_INPUT_STR = "{'country': 'France'}"
EXPECTED_TOOL_OUTPUT_STR = "{'output': 'Paris'}"
PYTHON_VERSION_OVER_3_9 = sys.version_info[:2] > (3, 9)


def get_capital(country: str) -> dict:
    """Return the capital of a country."""
    country = country.capitalize()
    capitals = {"France": "Paris", "Japan": "Tokyo"}
    return {"output": capitals.get(country, "Unknown")}


@pytest.fixture(scope="session")
def text_generation_metrics(is_streaming, is_chat):
    metric_name = "generate_content_stream" if is_streaming else "generate_content"

    chat_count = 2 if PYTHON_VERSION_OVER_3_9 else 1
    return [(f"Llm/completion/Gemini/{metric_name}", chat_count if is_chat else 1)]


@reset_core_stats_engine()
def test_gemini_tool(exercise_text_model, text_generation_metrics, set_trace_info, is_chat):
    # Expect one summary event, one message event for the input, and message event for the output
    @validate_custom_event_count(count=6 if (is_chat and PYTHON_VERSION_OVER_3_9) else 3)
    @validate_transaction_metrics(
        name="test_gemini_tool",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_tool")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        with WithLlmCustomAttributes({"context": "attr"}):
            exercise_text_model(
                model="gemini-3.5-flash",
                contents=PROMPT,
                config=google.genai.types.GenerateContentConfig(
                    max_output_tokens=500, temperature=0.7, tools=[get_capital]
                ),
            )

    _test()


@reset_core_stats_engine()
def test_gemini_multi_text_generation(exercise_text_model, text_generation_metrics, set_trace_info, is_chat):
    # Double all the metric counts for this test as we run the model twice
    text_generation_metrics = [
        (m[0], m[1] * (1 if (is_chat and PYTHON_VERSION_OVER_3_9) else 2)) for m in text_generation_metrics
    ]

    # Expect one summary event, one message event for the input, and message event for the output for each send_message_call
    @validate_custom_event_count(count=6)
    @validate_transaction_metrics(
        name="test_gemini_multi_text_generation",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_multi_text_generation")
    def _test():
        set_trace_info()
        exercise_text_model(
            model="gemini-3.5-flash",
            contents=PROMPT,
            config=google.genai.types.GenerateContentConfig(max_output_tokens=500, temperature=0.7),
        )
        exercise_text_model(
            model="gemini-3.5-flash",
            contents=PROMPT,
            config=google.genai.types.GenerateContentConfig(max_output_tokens=500, temperature=0.7),
        )

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_gemini_text_generation_outside_txn(exercise_text_model):
    exercise_text_model(
        model="gemini-3.5-flash",
        contents=PROMPT,
        config=google.genai.types.GenerateContentConfig(max_output_tokens=500, temperature=0.7),
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_gemini_text_generation_ai_monitoring_disabled(exercise_text_model):
    exercise_text_model(
        model="gemini-3.5-flash",
        contents=PROMPT,
        config=google.genai.types.GenerateContentConfig(max_output_tokens=500, temperature=0.7),
    )
