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
import pytest

from newrelic.api.background_task import background_task

enabled_ml_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": True,
}

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)


@background_task()
def test_invalid_request_error_model_does_not_exist():
    with pytest.raises(openai.InvalidRequestError):
        openai.ChatCompletion.create(
            model="does-not-exist",
            messages=(
                {"role": "system", "content": "Model does not exist."},
                {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
            ),
            temperature=0.7,
            max_tokens=100,
        )


@background_task()
def test_authentication_error_invalid_api_key(monkeypatch):
    monkeypatch.setattr(openai, "api_key", "InvalidKey")
    with pytest.raises(openai.error.AuthenticationError):
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=(
                {"role": "system", "content": "Invalid API key."},
                {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
            ),
            temperature=0.7,
            max_tokens=100,
        )
