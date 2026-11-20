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

# Unambiguous region prefix -> ARN partition. Must be updated when AWS adds a partition. See
# https://github.com/aws/aws-sdk-js-v3/blob/main/packages-internal/util-endpoints/src/lib/aws/partitions.json
_PARTITION_REGION_PREFIXES = (
    ("aws-cn-global", "aws-cn"),
    ("cn-", "aws-cn"),
    ("aws-us-gov-global", "aws-us-gov"),
    ("us-gov-", "aws-us-gov"),
    ("aws-iso-global", "aws-iso"),
    ("us-iso-", "aws-iso"),
    ("aws-iso-b-global", "aws-iso-b"),
    ("us-isob-", "aws-iso-b"),
    ("aws-iso-e-global", "aws-iso-e"),
    ("eu-isoe-", "aws-iso-e"),
    ("aws-iso-f-global", "aws-iso-f"),
    ("us-isof-", "aws-iso-f"),
    ("eusc-", "aws-eusc"),
)


def get_aws_partition(region):
    """Determine the ARN partition from an AWS region name. Defaults to `aws`."""
    if isinstance(region, str):
        region = region.lower()
        for prefix, partition in _PARTITION_REGION_PREFIXES:
            if region.startswith(prefix):
                return partition
    return "aws"
