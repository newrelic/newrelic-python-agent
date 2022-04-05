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

import sqlite3
import newrelic.packages.six as six
import pytest

from testing_support.fixtures import override_application_settings, dt_enabled
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper

from _test_code_level_metrics import exercise_function, CLASS_INSTANCE, CLASS_INSTANCE_CALLABLE, exercise_lambda, ExerciseClass, ExerciseClassCallable, __file__ as FILE_PATH


NAMESPACE = "_test_code_level_metrics"
CLASS_NAMESPACE = ".".join((NAMESPACE, "ExerciseClass"))
CALLABLE_CLASS_NAMESPACE = ".".join((NAMESPACE, "ExerciseClassCallable"))
FUZZY_NAMESPACE = CLASS_NAMESPACE if six.PY3 else NAMESPACE
if FILE_PATH.endswith(".pyc"):
    FILE_PATH = FILE_PATH[:-1]

SQLITE_CONNECTION = sqlite3.Connection(":memory:")

@pytest.mark.parametrize(
    "func,args,agents",
    (
        (  # Function
            exercise_function,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_function",
                "code.lineno": 14,
                "code.namespace": NAMESPACE,
            },
        ),
        (  # Method
            CLASS_INSTANCE.exercise_method,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_method",
                "code.lineno": 19,
                "code.namespace": CLASS_NAMESPACE,
            },
        ),
        (  # Static Method
            CLASS_INSTANCE.exercise_static_method,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_static_method",
                "code.lineno": 22,
                "code.namespace": FUZZY_NAMESPACE,
            },
        ),
        (  # Class Method
            ExerciseClass.exercise_class_method,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "exercise_class_method",
                "code.lineno": 26,
                "code.namespace": CLASS_NAMESPACE,
            },
        ),
        (  # Callable object
            CLASS_INSTANCE_CALLABLE,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "__call__",
                "code.lineno": 32,
                "code.namespace": CALLABLE_CLASS_NAMESPACE,
            },
        ),
        (  # Lambda
            exercise_lambda,
            (),
            {
                "code.filepath": FILE_PATH,
                "code.function": "<lambda>",
                "code.lineno": 38,
                "code.namespace": NAMESPACE,
            },
        ),
        (  # Top Level Builtin
            max,
            (1, 2),
            {
                "code.filepath": "<builtin>",
                "code.function": "max",
                "code.lineno": None,
                "code.namespace": "builtins",
            },
        ),
        (  # Module Level Builtin
            sqlite3.connect,
            (":memory:",),
            {
                "code.filepath": "<builtin>",
                "code.function": "connect",
                "code.lineno": None,
                "code.namespace": "_sqlite3",
            },
        ),
        (  # Builtin Method
            SQLITE_CONNECTION.__enter__,
            (),
            {
                "code.filepath": "<builtin>",
                "code.function": "__enter__",
                "code.lineno": None,
                "code.namespace": "sqlite3.Connection",
            },
        ),
    ),
)
def test_code_level_metrics_callables(func, args, agents):
    @override_application_settings({
        "code_level_metrics.enabled": True,
    })
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        FunctionTraceWrapper(func)(*args)

    _test()


@pytest.mark.parametrize(
    "obj,agents",
    (
        (  # Class with __call__
            ExerciseClassCallable,
            {
                "code.filepath": FILE_PATH,
                "code.function": "ExerciseClassCallable",
                "code.lineno": 31,
                "code.namespace":NAMESPACE,
            },
        ),
        (  # Class without __call__
            ExerciseClass,
            {
                "code.filepath": FILE_PATH,
                "code.function": "ExerciseClass",
                "code.lineno": 18,
                "code.namespace": NAMESPACE,
            },
        ),
        (  # Non-callable Object instance
            CLASS_INSTANCE,
            {
                "code.filepath": FILE_PATH,
                "code.function": "ExerciseClass",
                "code.lineno": 18,
                "code.namespace": NAMESPACE,
            },
        ),
    ),
)
def test_code_level_metrics_objects(obj, agents):
    @override_application_settings({
        "code_level_metrics.enabled": True,
    })
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        with FunctionTrace("_test", source=obj):
            pass
    
    _test()