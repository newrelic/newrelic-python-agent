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

from newrelic.common.aws import get_aws_partition


@pytest.mark.parametrize(
    "region,expected",
    [
        ("us-east-1", "aws"),
        ("eu-west-1", "aws"),
        ("cn-north-1", "aws-cn"),
        ("us-gov-west-1", "aws-us-gov"),
        ("us-iso-east-1", "aws-iso"),
        ("us-isob-east-1", "aws-iso-b"),
        ("eu-isoe-west-1", "aws-iso-e"),
        ("us-isof-south-1", "aws-iso-f"),
        ("eusc-de-east-1", "aws-eusc"),
        ("CN-NORTH-1", "aws-cn"),
        ("localstack", "aws"),
        ("", "aws"),
        (None, "aws"),
    ],
)
def test_get_aws_partition(region, expected):
    assert get_aws_partition(region) == expected
