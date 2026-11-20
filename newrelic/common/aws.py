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

# Unambiguous DNS suffix -> ARN partition. See
# https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html
_PARTITION_DNS_SUFFIXES = (
    (".amazonaws.com.cn", "aws-cn"),
    (".amazonaws.eu", "aws-eusc"),
    (".c2s.ic.gov", "aws-iso"),
    (".sc2s.sgov.gov", "aws-iso-b"),
    (".cloud.adc-e.uk", "aws-iso-e"),
    (".csp.hci.ic.gov", "aws-iso-f"),
)


def get_aws_partition(host):
    """Determine the ARN partition from an AWS endpoint host name. Defaults to `aws`."""
    try:
        host = host.lower().split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0].rstrip(".")
        for suffix, partition in _PARTITION_DNS_SUFFIXES:
            if host.endswith(suffix):
                return partition
            
        # GovCloud shares the .amazonaws.com suffix with the standard partition, so the region must be checked.
        if host.endswith(".amazonaws.com") and any(label.startswith("us-gov-") for label in host.split(".")):
            return "aws-us-gov"
    except Exception:
        pass
    return "aws"
