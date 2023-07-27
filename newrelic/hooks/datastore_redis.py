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

import re

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

_redis_client_methods = {
    "acl_cat",
    "acl_deluser",
    "acl_dryrun",
    "acl_genpass",
    "acl_getuser",
    "acl_help",
    "acl_list",
    "acl_load",
    "acl_log_reset",
    "acl_log",
    "acl_save",
    "acl_setuser",
    "acl_users",
    "acl_whoami",
    "add_document_hash",
    "add_document",
    "add",
    "addnx",
    "aggregate",
    "aliasadd",
    "aliasdel",
    "aliasupdate",
    "alter_schema_add",
    "alter",
    "append",
    "arrappend",
    "arrindex",
    "arrinsert",
    "arrlen",
    "arrpop",
    "arrtrim",
    "auth",
    "bgrewriteaof",
    "bgsave",
    "bitcount",
    "bitfield",
    "bitfield_ro",
    "bitop_and",
    "bitop_not",
    "bitop_or",
    "bitop_xor",
    "bitop",
    "bitpos",
    "blmove",
    "blmpop",
    "blpop",
    "brpop",
    "brpoplpush",
    "byrank",
    "byrevrank",
    "bzmpop",
    "bzpopmax",
    "bzpopmin",
    "card",
    "cdf",
    "clear",
    "client_getname",
    "client_getredir",
    "client_id",
    "client_info",
    "client_kill_filter",
    "client_kill",
    "client_list",
    "client_no_evict",
    "client_pause",
    "client_reply",
    "client_setname",
    "client_tracking",
    "client_trackinginfo",
    "client_unblock",
    "client_unpause",
    "client",
    "cluster_add_slots",
    "cluster_addslots",
    "cluster_count_failure_report",
    "cluster_count_failure_reports",
    "cluster_count_key_in_slots",
    "cluster_countkeysinslot",
    "cluster_del_slots",
    "cluster_delslots",
    "cluster_failover",
    "cluster_forget",
    "cluster_get_keys_in_slot",
    "cluster_get_keys_in_slots",
    "cluster_info",
    "cluster_keyslot",
    "cluster_meet",
    "cluster_nodes",
    "cluster_replicate",
    "cluster_reset_all_nodes",
    "cluster_reset",
    "cluster_save_config",
    "cluster_set_config_epoch",
    "cluster_setslot",
    "cluster_slaves",
    "cluster_slots",
    "cluster",
    "command_count",
    "command_docs",
    "command_getkeys",
    "command_getkeysandflags",
    "command_info",
    "command_list",
    "command",
    "commit",
    "config_get",
    "config_resetstat",
    "config_rewrite",
    "config_set",
    "config",
    "copy",
    "count",
    "create_index",
    "create",
    "createrule",
    "dbsize",
    "debug_object",
    "debug_segfault",
    "debug_sleep",
    "debug",
    "decr",
    "decrby",
    "delete_document",
    "delete",
    "deleterule",
    "dict_add",
    "dict_del",
    "dict_dump",
    "drop_index",
    "dropindex",
    "dump",
    "echo",
    "eval_ro",
    "eval",
    "evalsha_ro",
    "evalsha",
    "execution_plan",
    "exists",
    "expire",
    "expireat",
    "expiretime",
    "explain_cli",
    "explain",
    "failover",
    "fcall_ro",
    "fcall",
    "flushall",
    "flushdb",
    "forget",
    "function_delete",
    "function_dump",
    "function_flush",
    "function_kill",
    "function_list",
    "function_load",
    "function_restore",
    "function_stats",
    "geoadd",
    "geodist",
    "geohash",
    "geopos",
    "georadius",
    "georadiusbymember",
    "geosearch",
    "geosearchstore",
    "get",
    "getbit",
    "getdel",
    "getex",
    "getrange",
    "getset",
    "hdel",
    "hello",
    "hexists",
    "hget",
    "hgetall",
    "hincrby",
    "hincrbyfloat",
    "hkeys",
    "hlen",
    "hmget",
    "hmset_dict",
    "hmset",
    "hrandfield",
    "hscan_inter",
    "hscan",
    "hset",
    "hsetnx",
    "hstrlen",
    "hvals",
    "incr",
    "incrby",
    "incrbyfloat",
    "info",
    "initbydim",
    "initbyprob",
    "insert",
    "insertnx",
    "keys",
    "lastsave",
    "latency_doctor",
    "latency_graph",
    "latency_histogram",
    "latency_history",
    "latency_latest",
    "latency_reset",
    "lcs",
    "lindex",
    "linsert",
    "list",
    "llen",
    "lmove",
    "lmpop",
    "loadchunk",
    "lolwut",
    "lpop",
    "lpos",
    "lpush",
    "lpushx",
    "lrange",
    "lrem",
    "lset",
    "ltrim",
    "madd",
    "max",
    "memory_doctor",
    "memory_help",
    "memory_malloc_stats",
    "memory_purge",
    "memory_stats",
    "memory_usage",
    "merge",
    "mexists",
    "mget",
    "migrate_keys",
    "migrate",
    "min",
    "module_list",
    "module_load",
    "module_loadex",
    "module_unload",
    "monitor",
    "move",
    "mrange",
    "mrevrange",
    "mset",
    "msetnx",
    "numincrby",
    "object_encoding",
    "object_idletime",
    "object_refcount",
    "object",
    "objkeys",
    "objlen",
    "persist",
    "pexpire",
    "pexpireat",
    "pexpiretime",
    "pfadd",
    "pfcount",
    "pfmerge",
    "ping",
    "profile",
    "psetex",
    "psubscribe",
    "psync",
    "pttl",
    "publish",
    "pubsub_channels",
    "pubsub_numpat",
    "pubsub_numsub",
    "pubsub",
    "punsubscribe",
    "quantile",
    "query",
    "queryindex",
    "quit",
    "randomkey",
    "range",
    "rank",
    "readonly",
    "readwrite",
    "rename",
    "renamenx",
    "replicaof",
    "reserve",
    "reset",
    "resp",
    "restore",
    "revrange",
    "revrank",
    "role",
    "rpop",
    "rpoplpush",
    "rpush",
    "rpushx",
    "sadd",
    "save",
    "scan_iter",
    "scan",
    "scandump",
    "scard",
    "script_debug",
    "script_exists",
    "script_flush",
    "script_kill",
    "script_load",
    "sdiff",
    "sdiffstore",
    "search",
    "select",
    "sentinel_ckquorum",
    "sentinel_failover",
    "sentinel_flushconfig",
    "sentinel_get_master_addr_by_name",
    "sentinel_master",
    "sentinel_masters",
    "sentinel_monitor",
    "sentinel_remove",
    "sentinel_reset",
    "sentinel_sentinels",
    "sentinel_set",
    "sentinel_slaves",
    "set",
    "setbit",
    "setex",
    "setnx",
    "setrange",
    "shutdown",
    "sinter",
    "sintercard",
    "sinterstore",
    "sismember",
    "slaveof",
    "slowlog_get",
    "slowlog_len",
    "slowlog_reset",
    "slowlog",
    "smembers",
    "smismember",
    "smove",
    "sort_ro",
    "sort",
    "spellcheck",
    "spop",
    "srandmember",
    "srem",
    "sscan_iter",
    "sscan",
    "stralgo",
    "strappend",
    "strlen",
    "subscribe",
    "substr",
    "sugadd",
    "sugdel",
    "sugget",
    "suglen",
    "sunion",
    "sunionstore",
    "swapdb",
    "sync",
    "syndump",
    "synupdate",
    "tagvals",
    "time",
    "toggle",
    "touch",
    "trimmed_mean",
    "ttl",
    "type",
    "unlink",
    "unsubscribe",
    "unwatch",
    "wait",
    "waitaof",
    "watch",
    "xack",
    "xadd",
    "xautoclaim",
    "xclaim",
    "xdel",
    "xgroup_create",
    "xgroup_createconsumer",
    "xgroup_del_consumer",
    "xgroup_delconsumer",
    "xgroup_destroy",
    "xgroup_set_id",
    "xgroup_setid",
    "xinfo_consumers",
    "xinfo_groups",
    "xinfo_help",
    "xinfo_stream",
    "xlen",
    "xpending_range",
    "xpending",
    "xrange",
    "xread_group",
    "xread",
    "xreadgroup",
    "xrevrange",
    "xtrim",
    "zadd",
    "zaddoption",
    "zcard",
    "zcount",
    "zdiff",
    "zdiffstore",
    "zincrby",
    "zinter",
    "zintercard",
    "zinterstore",
    "zlexcount",
    "zmpop",
    "zmscore",
    "zpopmax",
    "zpopmin",
    "zrandmember",
    "zrange",
    "zrangebylex",
    "zrangebyscore",
    "zrangestore",
    "zrank",
    "zrem",
    "zremrangebylex",
    "zremrangebyrank",
    "zremrangebyscore",
    "zrevrange",
    "zrevrangebylex",
    "zrevrangebyscore",
    "zrevrank",
    "zscan_iter",
    "zscan",
    "zscore",
    "zunion",
    "zunionstore",
}

_redis_multipart_commands = set(["client", "cluster", "command", "config", "debug", "sentinel", "slowlog", "script"])

_redis_operation_re = re.compile(r"[-\s]+")


def _conn_attrs_to_dict(connection):
    return {
        "host": getattr(connection, "host", None),
        "port": getattr(connection, "port", None),
        "path": getattr(connection, "path", None),
        "db": getattr(connection, "db", None),
    }


def _instance_info(kwargs):
    host = kwargs.get("host") or "localhost"
    port_path_or_id = str(kwargs.get("path") or kwargs.get("port", "unknown"))
    db = str(kwargs.get("db") or 0)

    return (host, port_path_or_id, db)


def _wrap_Redis_method_wrapper_(module, instance_class_name, operation):
    def _nr_wrapper_Redis_method_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        dt = DatastoreTrace(product="Redis", target=None, operation=operation, source=wrapped)

        transaction._nr_datastore_instance_info = (None, None, None)

        with dt:
            result = wrapped(*args, **kwargs)

            host, port_path_or_id, db = transaction._nr_datastore_instance_info
            dt.host = host
            dt.port_path_or_id = port_path_or_id
            dt.database_name = db

            return result

    name = "%s.%s" % (instance_class_name, operation)
    wrap_function_wrapper(module, name, _nr_wrapper_Redis_method_)


def _nr_Connection_send_command_wrapper_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None or not args:
        return wrapped(*args, **kwargs)

    host, port_path_or_id, db = (None, None, None)

    try:
        dt = transaction.settings.datastore_tracer
        if dt.instance_reporting.enabled or dt.database_name_reporting.enabled:
            conn_kwargs = _conn_attrs_to_dict(instance)
            host, port_path_or_id, db = _instance_info(conn_kwargs)
    except:
        pass

    transaction._nr_datastore_instance_info = (host, port_path_or_id, db)

    # Older Redis clients would when sending multi part commands pass
    # them in as separate arguments to send_command(). Need to therefore
    # detect those and grab the next argument from the set of arguments.

    operation = args[0].strip().lower()

    # If it's not a multi part command, there's no need to trace it, so
    # we can return early.

    if operation.split()[0] not in _redis_multipart_commands:
        return wrapped(*args, **kwargs)

    # Convert multi args to single arg string

    if operation in _redis_multipart_commands and len(args) > 1:
        operation = "%s %s" % (operation, args[1].strip().lower())

    operation = _redis_operation_re.sub("_", operation)

    with DatastoreTrace(
        product="Redis",
        target=None,
        operation=operation,
        host=host,
        port_path_or_id=port_path_or_id,
        database_name=db,
        source=wrapped,
    ):
        return wrapped(*args, **kwargs)


def instrument_redis_client(module):
    if hasattr(module, "StrictRedis"):
        for name in _redis_client_methods:
            if name in vars(module.StrictRedis):
                _wrap_Redis_method_wrapper_(module, "StrictRedis", name)

    if hasattr(module, "Redis"):
        for name in _redis_client_methods:
            if name in vars(module.Redis):
                _wrap_Redis_method_wrapper_(module, "Redis", name)


def instrument_redis_commands_core(module):
    _instrument_redis_commands_module(module, "CoreCommands")


def instrument_redis_commands_sentinel(module):
    _instrument_redis_commands_module(module, "SentinelCommands")


def instrument_redis_commands_json_commands(module):
    _instrument_redis_commands_module(module, "JSONCommands")


def instrument_redis_commands_search_commands(module):
    _instrument_redis_commands_module(module, "SearchCommands")


def instrument_redis_commands_timeseries_commands(module):
    _instrument_redis_commands_module(module, "TimeSeriesCommands")


def instrument_redis_commands_graph_commands(module):
    _instrument_redis_commands_module(module, "GraphCommands")


def instrument_redis_commands_bf_commands(module):
    _instrument_redis_commands_module(module, "BFCommands")
    _instrument_redis_commands_module(module, "CFCommands")
    _instrument_redis_commands_module(module, "CMSCommands")
    _instrument_redis_commands_module(module, "TDigestCommands")
    _instrument_redis_commands_module(module, "TOPKCommands")


def instrument_redis_commands_cluster(module):
    _instrument_redis_commands_module(module, "RedisClusterCommands")


def _instrument_redis_commands_module(module, class_name):
    for name in _redis_client_methods:
        if hasattr(module, class_name):
            class_instance = getattr(module, class_name)
            if hasattr(class_instance, name):
                _wrap_Redis_method_wrapper_(module, class_name, name)


def instrument_redis_connection(module):
    wrap_function_wrapper(module, "Connection.send_command", _nr_Connection_send_command_wrapper_)
