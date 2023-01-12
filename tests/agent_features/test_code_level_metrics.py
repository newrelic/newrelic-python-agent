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
import sys

import pytest
from _test_code_level_metrics import (
    CLASS_INSTANCE,
    CLASS_INSTANCE_CALLABLE,
    TYPE_CONSTRUCTOR_CALLABLE_CLASS_INSTANCE,
    TYPE_CONSTRUCTOR_CLASS_INSTANCE,
    ExerciseClass,
    ExerciseClassCallable,
    ExerciseTypeConstructor,
    ExerciseTypeConstructorCallable,
)
from _test_code_level_metrics import __file__ as FILE_PATH
from _test_code_level_metrics import (
    exercise_function,
    exercise_lambda,
    exercise_partial,
)
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events

import newrelic.packages.six as six
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace

is_pypy = hasattr(sys, "pypy_version_info")

NAMESPACE = "_test_code_level_metrics"
CLASS_NAMESPACE = ".".join((NAMESPACE, "ExerciseClass"))
CALLABLE_CLASS_NAMESPACE = ".".join((NAMESPACE, "ExerciseClassCallable"))
TYPE_CONSTRUCTOR_NAMESPACE = ".".join((NAMESPACE, "ExerciseTypeConstructor"))
TYPE_CONSTRUCTOR_CALLABLE_NAMESPACE = ".".join((NAMESPACE, "ExerciseTypeConstructorCallable"))
FUZZY_NAMESPACE = CLASS_NAMESPACE if six.PY3 else NAMESPACE
if FILE_PATH.endswith(".pyc"):
    FILE_PATH = FILE_PATH[:-1]

SQLITE_CONNECTION = sqlite3.Connection(":memory:")

BUILTIN_ATTRS = {"code.filepath": "<builtin>", "code.lineno": None} if not is_pypy else {}


def merge_dicts(A, B):
    d = {}
    d.update(A)
    d.update(B)
    return d


@pytest.fixture
def extract():
    def _extract(obj):
        with FunctionTrace("_test", source=obj):
            pass

    return _extract


_TEST_BASIC_CALLABLES = {
    "function": (
        exercise_function,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_function",
            "code.lineno": 17,
            "code.namespace": NAMESPACE,
        },
    ),
    "lambda": (
        exercise_lambda,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "<lambda>",
            "code.lineno": 75,
            "code.namespace": NAMESPACE,
        },
    ),
    "partial": (
        exercise_partial,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_function",
            "code.lineno": 17,
            "code.namespace": NAMESPACE,
        },
    ),
    "builtin_function": (
        max,
        (1, 2),
        merge_dicts(
            {
                "code.function": "max",
                "code.namespace": "builtins" if six.PY3 else "__builtin__",
            },
            BUILTIN_ATTRS,
        ),
    ),
    "builtin_module_function": (
        sqlite3.connect,
        (":memory:",),
        merge_dicts(
            {
                "code.function": "connect",
                "code.namespace": "_sqlite3",
            },
            BUILTIN_ATTRS,
        ),
    ),
}


@pytest.mark.parametrize(
    "func,args,agents",
    [pytest.param(*args, id=id_) for id_, args in six.iteritems(_TEST_BASIC_CALLABLES)],
)
def test_code_level_metrics_basic_callables(func, args, agents, extract):
    @override_application_settings(
        {
            "code_level_metrics.enabled": True,
        }
    )
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        extract(func)

    _test()


_TEST_METHODS = {
    "method": (
        CLASS_INSTANCE.exercise_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_method",
            "code.lineno": 22,
            "code.namespace": CLASS_NAMESPACE,
        },
    ),
    "static_method": (
        CLASS_INSTANCE.exercise_static_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_static_method",
            "code.lineno": 25,
            "code.namespace": FUZZY_NAMESPACE,
        },
    ),
    "class_method": (
        ExerciseClass.exercise_class_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_class_method",
            "code.lineno": 29,
            "code.namespace": CLASS_NAMESPACE,
        },
    ),
    "call_method": (
        CLASS_INSTANCE_CALLABLE,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "__call__",
            "code.lineno": 35,
            "code.namespace": CALLABLE_CLASS_NAMESPACE,
        },
    ),
    "builtin_method": (
        SQLITE_CONNECTION.__enter__,
        (),
        merge_dicts(
            {
                "code.function": "__enter__",
                "code.namespace": "sqlite3.Connection" if not is_pypy else "_sqlite3.Connection",
            },
            BUILTIN_ATTRS,
        ),
    ),
}


@pytest.mark.parametrize(
    "func,args,agents",
    [pytest.param(*args, id=id_) for id_, args in six.iteritems(_TEST_METHODS)],
)
def test_code_level_metrics_methods(func, args, agents, extract):
    @override_application_settings(
        {
            "code_level_metrics.enabled": True,
        }
    )
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        extract(func)

    _test()


_TEST_TYPE_CONSTRUCTOR_METHODS = {
    "method": (
        TYPE_CONSTRUCTOR_CLASS_INSTANCE.exercise_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_method",
            "code.lineno": 39,
            "code.namespace": TYPE_CONSTRUCTOR_NAMESPACE,
        },
    ),
    "static_method": (
        TYPE_CONSTRUCTOR_CLASS_INSTANCE.exercise_static_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_static_method",
            "code.lineno": 43,
            "code.namespace": NAMESPACE,
        },
    ),
    "class_method": (
        ExerciseTypeConstructor.exercise_class_method,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "exercise_class_method",
            "code.lineno": 48,
            "code.namespace": TYPE_CONSTRUCTOR_NAMESPACE,
        },
    ),
    "lambda_method": (
        ExerciseTypeConstructor.exercise_lambda,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "<lambda>",
            "code.lineno": 61,
            # Lambdas behave strangely in type constructors on Python 2 and use the class namespace.
            "code.namespace": NAMESPACE if six.PY3 else TYPE_CONSTRUCTOR_NAMESPACE,
        },
    ),
    "call_method": (
        TYPE_CONSTRUCTOR_CALLABLE_CLASS_INSTANCE,
        (),
        {
            "code.filepath": FILE_PATH,
            "code.function": "__call__",
            "code.lineno": 53,
            "code.namespace": TYPE_CONSTRUCTOR_CALLABLE_NAMESPACE,
        },
    ),
}


@pytest.mark.parametrize(
    "func,args,agents",
    [pytest.param(*args, id=id_) for id_, args in six.iteritems(_TEST_TYPE_CONSTRUCTOR_METHODS)],
)
def test_code_level_metrics_type_constructor_methods(func, args, agents, extract):
    @override_application_settings(
        {
            "code_level_metrics.enabled": True,
        }
    )
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        extract(func)

    _test()


_TEST_OBJECTS = {
    "class": (
        ExerciseClass,
        {
            "code.filepath": FILE_PATH,
            "code.function": "ExerciseClass",
            "code.lineno": 21,
            "code.namespace": NAMESPACE,
        },
    ),
    "callable_class": (
        ExerciseClassCallable,
        {
            "code.filepath": FILE_PATH,
            "code.function": "ExerciseClassCallable",
            "code.lineno": 34,
            "code.namespace": NAMESPACE,
        },
    ),
    "type_constructor_class": (
        ExerciseTypeConstructor,
        {
            "code.filepath": FILE_PATH,
            "code.function": "ExerciseTypeConstructor",
            "code.namespace": NAMESPACE,
        },
    ),
    "type_constructor_class_callable_class": (
        ExerciseTypeConstructorCallable,
        {
            "code.filepath": FILE_PATH,
            "code.function": "ExerciseTypeConstructorCallable",
            "code.namespace": NAMESPACE,
        },
    ),
    "non_callable_object": (
        CLASS_INSTANCE,
        {
            "code.filepath": FILE_PATH,
            "code.function": "ExerciseClass",
            "code.lineno": 21,
            "code.namespace": NAMESPACE,
        },
    ),
}


@pytest.mark.parametrize(
    "obj,agents",
    [pytest.param(*args, id=id_) for id_, args in six.iteritems(_TEST_OBJECTS)],
)
def test_code_level_metrics_objects(obj, agents, extract):
    @override_application_settings(
        {
            "code_level_metrics.enabled": True,
        }
    )
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_agents=agents,
    )
    @background_task()
    def _test():
        extract(obj)

    _test()
