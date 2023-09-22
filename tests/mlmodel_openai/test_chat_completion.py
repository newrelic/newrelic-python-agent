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


@pytest.fixture
def run_openai_chat_completion_sync():
    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a scientist."},
            {"role": "user", "content": "What is the boiling point of water?"},
            {"role": "assistant", "content": "The boiling point of water is 212 degrees Fahrenheit."},
            {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
        ],
    )


@pytest.fixture
def run_openai_chat_completion_async():
    openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a scientist."},
            {"role": "user", "content": "What is the boiling point of water?"},
            {
                "role": "assistant",
                "content": "The boiling point of water is 212 degrees Fahrenheit or 100 degrees Celsius.",
            },
        ],
    )


def test_no_harm():
    pass
