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
import redis

from testing_support.db_settings import redis_settings

DB_SETTINGS = redis_settings()[0]

redis_client = redis.Redis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)
strict_redis_client = redis.StrictRedis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)


IGNORED_METHODS = {
    'MODULE_CALLBACKS',
    'MODULE_VERSION',
    'NAME',
    "append_bucket_size",
    "append_capacity",
    "append_error",
    "append_expansion",
    "append_items_and_increments",
    "append_items",
    "append_max_iterations",
    "append_no_create",
    "append_no_scale",
    "append_values_and_weights",
    "append_weights",
    "client_tracking_off",
    "client_tracking_on",
    "client",
    "close",
    "commandmixin",
    "connection_pool",
    "connection",
    "debug_segfault",
    "execute_command",
    "from_url",
    "get_connection_kwargs",
    "get_encoder",
    "hscan_iter",
    "load_external_module",
    "lock",
    "parse_response",
    "pipeline",
    "register_script",
    "response_callbacks",
    "RESPONSE_CALLBACKS",
    "sentinel",
    "sentinel",
    "set_file",
    "set_path",
    "set_response_callback",
    "transaction",
    "BatchIndexer",
    "batch_indexer",
    "get_params_args",
    "index_name",
    "load_document",
    "add_edge",
    "add_node",
    "bulk",
    "call_procedure",
    "edges",
    "flush",
    "get_label",
    "get_property",
    "get_relation",
    "labels",
    "list_keys",
    "name",
    "nodes",
    "property_keys",
    "relationship_types",
    "version",

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


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
def test_uninstrumented_methods(client):
    methods = {m for m in dir(client) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(client, m), "__wrapped__")
    uninstrumented = {m for m in methods - IGNORED_METHODS if not is_wrapped(m)}

    for module in REDIS_MODULES:
        module_client = getattr(client, module)()
        module_methods = {m for m in dir(module_client) if not m[0] == "_"}
        is_wrapped = lambda m: hasattr(getattr(module_client, m), "__wrapped__")
        uninstrumented |= {m for m in module_methods - IGNORED_METHODS if not is_wrapped(m)}

    assert not uninstrumented, "Uninstrumented methods: %s" % sorted(uninstrumented)
