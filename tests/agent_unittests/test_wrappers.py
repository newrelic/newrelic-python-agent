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

from newrelic.common.object_wrapper import function_wrapper


@pytest.fixture(scope="function")
def wrapper():
    @function_wrapper
    def _wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    return _wrapper


@pytest.fixture(scope="function")
def wrapped_function(wrapper):
    @wrapper
    def wrapped():
        return True

    return wrapped


def test_nr_prefix_attributes(wrapped_function):
    wrapped_function._nr_attr = 1
    vars_ = vars(wrapped_function)

    assert wrapped_function._nr_attr == 1, "_nr_ attributes should be stored on wrapper object and retrievable."
    assert "_nr_attr" not in vars_, "_nr_ attributes should NOT appear in __dict__."


def test_self_prefix_attributes(wrapped_function):
    wrapped_function._self_attr = 1
    vars_ = vars(wrapped_function)

    assert wrapped_function._self_attr == 1, "_self_ attributes should be stored on wrapper object and retrievable."
    assert "_nr_attr" not in vars_, "_self_ attributes should NOT appear in __dict__."


def test_prefixed_attributes_share_namespace(wrapped_function):
    wrapped_function._nr_attr = 1
    wrapped_function._self_attr = 2

    assert wrapped_function._nr_attr == 2, (
        "_nr_ attributes share a namespace with _self_ attributes and should be overwritten."
    )


def test_wrapped_function_attributes(wrapped_function):
    wrapped_function._other_attr = 1
    vars_ = vars(wrapped_function)

    assert wrapped_function._other_attr == 1, "All other attributes should be stored on wrapped object and retrievable."
    assert "_other_attr" in vars_, "Other types of attributes SHOULD appear in __dict__."

    assert wrapped_function()


def test_multiple_wrapper_last_object(wrapper):
    def wrapped():
        pass

    wrapper_1 = wrapper(wrapped)
    wrapper_2 = wrapper(wrapper_1)

    assert wrapper_2._nr_last_object is wrapped, "Last object in chain should be the wrapped function."
    assert wrapper_2._nr_next_object is wrapper_1, "Next object in chain should be the middle function."
