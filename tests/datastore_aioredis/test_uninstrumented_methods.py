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


IGNORED_METHODS = {
    "address",
    "auto_close_connection_pool",
    "channels",
    "client_tracking_off",
    "client_tracking_on",
    "client_no_touch",
    "close",
    "closed",
    "connection_pool",
    "connection",
    "db",
    "encoding",
    "execute_command",
    "execute",
    "from_url",
    "get_connection_kwargs",
    "get_encoder",
    "get_retry",
    "hscan_iter",
    "ihscan",
    "in_pubsub",
    "in_transaction",
    "initialize",
    "iscan",
    "isscan",
    "izscan",
    "load_external_module",
    "lock",
    "multi_exec",
    "parse_response",
    "patterns",
    "pipeline",
    "publish_json",
    "register_script",
    "response_callbacks",
    "RESPONSE_CALLBACKS",
    "sentinel",
    "SET_IF_EXIST",
    "SET_IF_NOT_EXIST",
    "set_response_callback",
    "set_retry",
    "SHUTDOWN_NOSAVE",
    "SHUTDOWN_SAVE",
    "single_connection_client",
    "transaction",
    "wait_closed",
    "xinfo",
    "ZSET_AGGREGATE_MAX",
    "ZSET_AGGREGATE_MIN",
    "ZSET_AGGREGATE_SUM",
    "ZSET_EXCLUDE_BOTH",
    "ZSET_EXCLUDE_MAX",
    "ZSET_EXCLUDE_MIN",
    "ZSET_IF_EXIST",
    "ZSET_IF_NOT_EXIST",
}

REDIS_MODULES = {
    "bf",
    "cf",
    "cms",
    "ft",
    "graph",
    "json",
    "tdigest",
    "topk",
    "ts",
}

IGNORED_METHODS |= REDIS_MODULES


def test_uninstrumented_methods(client):
    methods = {m for m in dir(client) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(client, m), "__wrapped__")
    uninstrumented = {m for m in methods - IGNORED_METHODS if not is_wrapped(m)}

    assert not uninstrumented, "Uninstrumented methods: %s" % sorted(uninstrumented)
