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

from testing_support.validators.validate_span_events import (
        validate_span_events)

from newrelic.api.background_task import background_task


# ===== Source Functions =====
def exercise():
    return


class MyClass():
    def exercise(self):
        return

    def __call__(self):
        return

CLASS_INSTANCE = MyClass()

exercise_lambda = lambda: None

# ===== Tests =====

@pytest.mark.parametrize("func", (
    exercise,  # Function
    CLASS_INSTANCE.exercise,  # Method
    CLASS_INSTANCE,  # Callable object
    exercise_lambda,  # Lambda
))
@validate_span_events(
    count=1,
    expected_agents=[
        "source_code_context.callable_name",
        "source_code_context.line_number",
        "source_code_context.file_path",
    ],
)
@background_task()
def test_source_code_context(func):
    func()
