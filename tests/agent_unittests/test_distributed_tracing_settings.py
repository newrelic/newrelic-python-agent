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

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_W3C = b"""
[newrelic]
distributed_tracing.exclude_newrelic_header = true
"""

# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_format', (
    (INI_FILE_EMPTY, {}, False),
    (INI_FILE_W3C, {}, True),
))
def test_distributed_trace_setings(ini, env, expected_format, global_settings):

    settings = global_settings()
    assert settings.distributed_tracing.exclude_newrelic_header == expected_format
