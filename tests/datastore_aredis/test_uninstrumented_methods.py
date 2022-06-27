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

import aredis

from testing_support.db_settings import redis_settings

DB_SETTINGS = redis_settings()[0]

strict_redis_client = aredis.StrictRedis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)


IGNORED_METHODS = {
    "cache",
    "connection_pool",
    "execute_command",
    "from_url",
    "hscan_iter",
    "lock",
    "NODES_FLAGS",
    "parse_response",
    "pipeline",
    "register_script",
    "response_callbacks",
    "RESPONSE_CALLBACKS",
    "RESULT_CALLBACKS",
    "sentinel",
    "set_response_callback",
    "transaction",
}

def test_uninstrumented_methods():
    methods = {m for m in dir(strict_redis_client) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(strict_redis_client, m), "__wrapped__")
    uninstrumented = {m for m in methods - IGNORED_METHODS if not is_wrapped(m)}

    assert not uninstrumented, "Uninstrumented methods: %s" % sorted(uninstrumented)
