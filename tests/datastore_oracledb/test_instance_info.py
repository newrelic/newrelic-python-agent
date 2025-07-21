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

import oracledb
import pytest

from newrelic.hooks.database_oracledb import instance_info

_instance_info_tests = [
    pytest.param(
        {"host": "localhost", "port": 8080, "service_name": "FREEPDB1"}, ("localhost", "8080", "FREEPDB1"), id="kwargs"
    ),
    pytest.param({"host": "localhost"}, ("localhost", "1521", "unknown"), id="kwargs_host_only"),
    pytest.param(
        {"params": oracledb.ConnectParams(host="localhost", port=8080, service_name="FREEPDB1")},
        ("localhost", "8080", "FREEPDB1"),
        id="connect_params_kwarg",
    ),
    pytest.param({"dsn": "user/password@localhost:8080/FREEPDB1"}, ("localhost", "8080", "FREEPDB1"), id="full_dsn"),
    pytest.param({"dsn": "localhost:8080/FREEPDB1"}, ("localhost", "8080", "FREEPDB1"), id="connect_string"),
    pytest.param({"dsn": "localhost:8080/"}, ("localhost", "8080", "unknown"), id="connect_string_no_service_name"),
    # These 2 will use the default port
    pytest.param({"dsn": "localhost/"}, ("localhost", "1521", "unknown"), id="connect_string_host_only"),
    pytest.param(
        {"dsn": "user/password@localhost/"}, ("localhost", "1521", "unknown"), id="dsn_credentials_and_host_only"
    ),
]


@pytest.mark.parametrize("kwargs,expected", _instance_info_tests)
def test_oracledb_instance_info(kwargs, expected):
    dsn = kwargs.pop("dsn", None)  # This is only a posarg
    args = (dsn,) if dsn else ()

    output = instance_info(args, kwargs)
    assert output == expected
