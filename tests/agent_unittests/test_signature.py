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
