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

from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTraceWrapper

import _test_source_code_context
from _test_source_code_context import exercise_function, CLASS_INSTANCE, exercise_lambda, ExerciseClass


FILE_PATH = _test_source_code_context.__file__


@pytest.mark.parametrize(
    "func,agents",
    (
        (  # Function
            exercise_function,
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_function",
                "code.lineno": 14,
                "code.namespace": "_test_source_code_context",
            },
        ),
        (  # Method
            CLASS_INSTANCE.exercise_method,
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_method",
                "code.lineno": 19,
                "code.namespace": "_test_source_code_context.ExerciseClass",
            },
        ),
        (  # Static Method
            CLASS_INSTANCE.exercise_static_method,
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_static_method",
                "code.lineno": 22,
                "code.namespace": "_test_source_code_context.ExerciseClass",
            },
        ),
        (  # Class Method
            ExerciseClass.exercise_class_method,
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_class_method",
                "code.lineno": 26,
                "code.namespace": "_test_source_code_context.ExerciseClass",
            },
        ),
        (  # Callable object
            CLASS_INSTANCE,
            {
                "code.filepath": FILE_PATH,
                "code.function": "ExerciseClass",
                "code.lineno": 14,
                "code.namespace": "_test_source_code_context.ExerciseClass",
            },
        ),
        (  # Lambda
            exercise_lambda,
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_lambda",
                "code.lineno": 36,
                "code.namespace": "_test_source_code_context",
            },
        ),
    ),
)
def test_source_code_context(func, agents):
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        FunctionTraceWrapper(func)()

    _test()
