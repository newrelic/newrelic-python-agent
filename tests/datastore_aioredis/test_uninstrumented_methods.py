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
import aioredis

from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname

DB_SETTINGS = redis_settings()[0]

redis_client = aioredis.Redis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)
strict_redis_client = aioredis.StrictRedis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)


IGNORED_METHODS = {
    "close",
    "connection_pool",
    "connection",
    "execute_command",
    "from_url",
    "initialize",
    "lock",
    "parse_response",
    "pipeline",
    "response_callbacks",
    "RESPONSE_CALLBACKS",
    "set_response_callback",
    "single_connection_client",
    "transaction",
    "hscan_iter",
    "register_script",
}


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
def test_uninstrumented_methods(client):
    methods = {m for m in dir(client) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(client, m), "__wrapped__")
    uninstrumented = {m for m in methods - IGNORED_METHODS if not is_wrapped(m)}

    assert not uninstrumented, "Uninstrumented methods: %s" % sorted(uninstrumented)
