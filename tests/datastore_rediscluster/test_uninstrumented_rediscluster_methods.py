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

import redis
from testing_support.db_settings import redis_cluster_settings

DB_CLUSTER_SETTINGS = redis_cluster_settings()[0]

# Set socket_timeout to 5s for fast fail, otherwise the default is to wait forever.
client = redis.RedisCluster(host=DB_CLUSTER_SETTINGS["host"], port=DB_CLUSTER_SETTINGS["port"], socket_timeout=5)

IGNORED_METHODS = {
    "MODULE_CALLBACKS",
    "MODULE_VERSION",
    "NAME",
    "add_edge",
    "add_node",
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
    "batch_indexer",
    "BatchIndexer",
    "bulk",
    "call_procedure",
    "client_tracking_off",
    "client_tracking_on",
    "client",
    "close",
    "commandmixin",
    "connection_pool",
    "connection",
    "debug_segfault",
    "edges",
    "execute_command",
    "flush",
    "from_url",
    "get_connection_kwargs",
    "get_encoder",
    "get_label",
    "get_params_args",
    "get_property",
    "get_relation",
    "get_retry",
    "hscan_iter",
    "index_name",
    "labels",
    "list_keys",
    "load_document",
    "load_external_module",
    "lock",
    "name",
    "nodes",
    "parse_response",
    "pipeline",
    "property_keys",
    "register_script",
    "relationship_types",
    "response_callbacks",
    "RESPONSE_CALLBACKS",
    "sentinel",
    "set_file",
    "set_path",
    "set_response_callback",
    "set_retry",
    "transaction",
    "version",
    "ALL_NODES",
    "CLUSTER_COMMANDS_RESPONSE_CALLBACKS",
    "COMMAND_FLAGS",
    "DEFAULT_NODE",
    "ERRORS_ALLOW_RETRY",
    "NODE_FLAGS",
    "PRIMARIES",
    "RANDOM",
    "REPLICAS",
    "RESULT_CALLBACKS",
    "RedisClusterRequestTTL",
    "SEARCH_COMMANDS",
    "client_no_touch",
    "cluster_addslotsrange",
    "cluster_bumpepoch",
    "cluster_delslotsrange",
    "cluster_error_retry_attempts",
    "cluster_flushslots",
    "cluster_links",
    "cluster_myid",
    "cluster_myshardid",
    "cluster_replicas",
    "cluster_response_callbacks",
    "cluster_setslot_stable",
    "cluster_shards",
    "command_flags",
    "commands_parser",
    "determine_slot",
    "disconnect_connection_pools",
    "encoder",
    "get_default_node",
    "get_node",
    "get_node_from_key",
    "get_nodes",
    "get_primaries",
    "get_random_node",
    "get_redis_connection",
    "get_replicas",
    "keyslot",
    "mget_nonatomic",
    "monitor",
    "mset_nonatomic",
    "node_flags",
    "nodes_manager",
    "on_connect",
    "pubsub",
    "read_from_replicas",
    "reinitialize_counter",
    "reinitialize_steps",
    "replace_default_node",
    "result_callbacks",
    "set_default_node",
    "user_on_connect_func",
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


def test_uninstrumented_methods():
    methods = {m for m in dir(client) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(client, m), "__wrapped__")
    uninstrumented = {m for m in methods - IGNORED_METHODS if not is_wrapped(m)}

    for module in REDIS_MODULES:
        if hasattr(client, module):
            module_client = getattr(client, module)()
            module_methods = {m for m in dir(module_client) if not m[0] == "_"}
            is_wrapped = lambda m: hasattr(getattr(module_client, m), "__wrapped__")
            uninstrumented |= {m for m in module_methods - IGNORED_METHODS if not is_wrapped(m)}

    assert not uninstrumented, "Uninstrumented methods: %s" % sorted(uninstrumented)
