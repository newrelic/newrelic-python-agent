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

from newrelic.common.encoding_utils import camel_case, snake_case


@pytest.mark.parametrize(
    "input_,expected,upper",
    [
        ("", "", False),
        ("", "", True),
        ("my_string", "myString", False),
        ("my_string", "MyString", True),
        ("LeaveCase", "LeaveCase", False),
        ("correctCase", "CorrectCase", True),
        ("UPPERcaseLETTERS", "UPPERcaseLETTERS", False),
        ("UPPERcaseLETTERS", "UPPERcaseLETTERS", True),
        ("lowerCASEletters", "lowerCASEletters", False),
        ("lowerCASEletters", "LowerCASEletters", True),
        ("very_long_snake_string", "VeryLongSnakeString", True),
        ("kebab-case", "kebab-case", False),
    ],
)
def test_camel_case(input_, expected, upper):
    output = camel_case(input_, upper=upper)
    assert output == expected


@pytest.mark.parametrize(
    "input_,expected",
    [
        ("", ""),
        ("", ""),
        ("my_string", "my_string"),
        ("myString", "my_string"),
        ("MyString", "my_string"),
        ("UPPERcaseLETTERS", "uppercase_letters"),
        ("lowerCASEletters", "lower_caseletters"),
        ("VeryLongCamelString", "very_long_camel_string"),
        ("kebab-case", "kebab-case"),
    ],
)
def test_snake_case(input_, expected):
    output = snake_case(input_)
    assert output == expected
