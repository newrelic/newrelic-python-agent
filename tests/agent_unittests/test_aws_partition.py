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
    "host,expected",
    [
        ("kinesis.us-east-1.amazonaws.com", "aws"),
        ("kinesis.eu-west-1.api.aws", "aws"),
        ("kinesis.us-gov-west-1.amazonaws.com", "aws-us-gov"),
        ("firehose.cn-north-1.amazonaws.com.cn", "aws-cn"),
        ("kinesis.eusc-de-east-1.amazonaws.eu", "aws-eusc"),
        ("kinesis.us-iso-east-1.c2s.ic.gov", "aws-iso"),
        ("kinesis.us-isob-east-1.sc2s.sgov.gov", "aws-iso-b"),
        ("kinesis.eu-isoe-west-1.cloud.adc-e.uk", "aws-iso-e"),
        ("kinesis.us-isof-south-1.csp.hci.ic.gov", "aws-iso-f"),
        ("KINESIS.CN-NORTH-1.AMAZONAWS.COM.CN:443", "aws-cn"),
        ("https://kinesis.cn-north-1.amazonaws.com.cn", "aws-cn"),
        ("https://kinesis.us-gov-west-1.amazonaws.com:443/path", "aws-us-gov"),
        ("localhost", "aws"),
        ("", "aws"),
        (None, "aws"),
    ],
)
def test_get_aws_partition(host, expected):
    assert get_aws_partition(host) == expected
