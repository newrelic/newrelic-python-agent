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

import functools

import pytest

from newrelic.common.signature import bind_args


@pytest.mark.parametrize(
    "func,args,kwargs,expected",
    [
        (lambda x, y: None, (1,), {"y": 2}, {"x": 1, "y": 2}),
        (lambda x=1, y=2: None, (1,), {"y": 2}, {"x": 1, "y": 2}),
        (lambda x=1: None, (), {}, {"x": 1}),
    ],
    ids=("posargs", "kwargs", "defaults"),
)
def test_signature_binding(func, args, kwargs, expected):
    bound_args = bind_args(func, args, kwargs)
    assert bound_args == expected


def decorator(f):
    @functools.wraps(f)
    def _decorator(*args, **kwargs):
        return f(*args, **kwargs)

    return _decorator


@decorator
def func(x, y=None):
    pass


@pytest.mark.parametrize(
    "unwrap,args,kwargs,expected",
    [
        (True, (1,), {"y": 2}, {"x": 1, "y": 2}),
        (False, (1,), {"y": 2}, {"args": (1,), "kwargs": {"y": 2}}),
        (True, (1,), {}, {"x": 1, "y": None}),
        (False, (1,), {}, {"args": (1,), "kwargs": {}}),
    ],
    ids=("unwrapped_standard", "wrapped_standard", "unwrapped_default", "wrapped_default"),
)
def test_wrapped_signature_binding(unwrap, args, kwargs, expected):
    bound_args = bind_args(func, args, kwargs, unwrap=unwrap)
    assert bound_args == expected
