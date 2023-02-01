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

from newrelic.common.function_signature_utils import bind_arguments
from newrelic.packages import six

if six.PY3:
    from _test_function_signature_utils_py3 import kwarg_only_func, posarg_only_func
else:
    kwarg_only_func, posarg_only_func = None, None

SKIPIF_PY2 = pytest.mark.skipif(six.PY2, reason="Positional and keyword only arguments not available in Python 2.")

EXPECTED = {"a": 1, "b": 2, "c": 3}


def required_arg_func(a, b, c):
    """All arguments are required."""
    pass


def default_arg_func(a=1, b=2, c=3):
    """All arguments have defaults."""
    pass


def wildcard_args_and_kwargs_func(a, *args, **kwargs):
    """Accepts indefinite number of args and kwargs."""
    pass


lambda_func = lambda a, b=2, c=3: None  # noqa: E731


class CallableObject(object):
    def __call__(self, a, b=2, c=3):
        pass

    def object_bound_method(self, a, b=2, c=3):
        pass

    @staticmethod
    def object_static_method(a, b=2, c=3):
        pass

    @classmethod
    def object_class_method(cls, a, b=2, c=3):
        pass


def test_posargs():
    """Tests required arguments specified through position."""
    assert bind_arguments(required_arg_func, 1, 2, 3) == EXPECTED


def test_kwargs():
    """Tests required arguments specified through keyword."""
    assert bind_arguments(required_arg_func, a=1, b=2, c=3) == EXPECTED


def test_mixed_args():
    """Tests mixed arguments and keyword arguments, with keyword arguments out of order."""
    assert bind_arguments(required_arg_func, 1, c=3, b=2) == EXPECTED


def test_default_args():
    """Tests default argument values when not specified."""
    assert bind_arguments(default_arg_func) == EXPECTED


def test_positional_default_args():
    """Tests default arguments through position."""
    assert bind_arguments(default_arg_func, 1, 2, 3) == EXPECTED


def test_keyword_default_args():
    """Tests default arguments through keyword."""
    assert bind_arguments(default_arg_func, a=1, b=2, c=3) == EXPECTED


def test_mixed_default_args():
    """Tests default arguments through position, keyword, and default values. Also specify keywords out of order."""
    assert bind_arguments(default_arg_func, 1, c=3) == EXPECTED


def test_wildcard_arguments():
    """Tests default arguments through position, keyword, and default values. Also specify keywords out of order."""
    expected = {"a": 1, "args": (4,), "kwargs": {"b": 2, "c": 3}}
    assert bind_arguments(wildcard_args_and_kwargs_func, 1, 4, b=2, c=3) == expected


@SKIPIF_PY2
def test_positional_only_args():
    """Tests positional only arguments, with a required, optional, and default positional arguments."""
    assert bind_arguments(posarg_only_func, 1, 2) == EXPECTED


@SKIPIF_PY2
def test_keyword_only_args():
    """Tests keyword only arguments, with a required, optional, and default keyword arguments. Also specify keywords out of order."""
    assert bind_arguments(kwarg_only_func, b=2, a=1) == EXPECTED


def test_lambdas():
    """Tests lambda functions with positional argument, keyword argument, and default argument values."""
    assert bind_arguments(lambda_func, 1, c=3) == EXPECTED


def test_callable_objects():
    """Tests callable object with positional argument, keyword argument, and default argument values."""
    bound_args = bind_arguments(CallableObject(), 1, c=3)
    bound_args.pop("self", None)  # Py2 has self argument
    assert bound_args == EXPECTED


def test_static_methods():
    """Tests static methods with positional argument, keyword argument, and default argument values."""
    assert bind_arguments(CallableObject.object_static_method, 1, c=3) == EXPECTED


def test_class_methods():
    """Tests class methods with positional argument, keyword argument, and default argument values."""
    bound_args = bind_arguments(CallableObject().object_class_method, 1, c=3)
    bound_args.pop("cls", None)  # Py2 has cls argument
    assert bound_args == EXPECTED


def test_bound_methods():
    """Tests bound methods with positional argument, keyword argument, and default argument values."""
    bound_args = bind_arguments(CallableObject().object_bound_method, 1, c=3)
    bound_args.pop("self", None)  # Py2 has self argument
    assert bound_args == EXPECTED
