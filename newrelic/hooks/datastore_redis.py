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

_redis_client_methods = (
    "xpending_range",
    "client_kill_filter",
    "acl_log_reset",
    "acl_cat",
    "acl_deluser",
    "acl_genpass",
    "acl_getuser",
    "acl_list",
    "acl_load",
    "acl_log",
    "acl_save",
    "acl_setuser",
    "acl_users",
    "acl_whoami",
    "append",
    "bgrewriteaof",
    "bgsave",
    "bitcount",
    "bitfield",
    "bitop",
    "bitpos",
    "blpop",
    "brpop",
    "brpoplpush",
    "bzpopmax",
    "bzpopmin",
    "client_getname",
    "client_id",
    "client_kill",
    "client_list",
    "client_pause",
    "client_setname",
    "client_unblock",
    "client",
    "cluster",
    "config_get",
    "config_resetstat",
    "config_rewrite",
    "config_set",
    "dbsize",
    "debug_object",
    "decr",
    "decrby",
    "delete",
    "dump",
    "echo",
    "eval",
    "evalsha",
    "exists",
    "expire",
    "expireat",
    "flushall",
    "flushdb",
    "geoadd",
    "geodist",
    "geohash",
    "geopos",
    "georadius",
    "georadiusbymember",
    "get",
    "getbit",
    "getrange",
    "getset",
    "hdel",
    "hexists",
    "hget",
    "hgetall",
    "hincrby",
    "hincrbyfloat",
    "hkeys",
    "hlen",
    "hmget",
    "hmset",
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
    "keys",
    "lastsave",
    "lindex",
    "linsert",
    "llen",
    "lpop",
    "lpos",
    "lpush",
    "lpushx",
    "lrange",
    "lrem",
    "lrem",
    "lset",
    "ltrim",
    "memory_purge",
    "memory_stats",
    "memory_usage",
    "mget",
    "migrate",
    "module_list",
    "module_load",
    "module_unload",
    "monitor",
    "move",
    "mset",
    "msetnx",
    "object",
    "persist",
    "pexpire",
    "pexpireat",
    "pfadd",
    "pfcount",
    "pfmerge",
    "ping",
    "psetex",
    "pttl",
    "publish",
    "pubsub_channels",
    "pubsub_numpat",
    "pubsub_numsub",
    "pubsub",
    "randomkey",
    "readonly",
    "readwrite",
    "rename",
    "renamenx",
    "restore",
    "rpop",
    "rpoplpush",
    "rpush",
    "rpushx",
    "sadd",
    "save",
    "scan_iter",
    "scan",
    "scard",
    "script_exists",
    "script_flush",
    "script_kill",
    "script_load",
    "sdiff",
    "sdiffstore",
    "sentinel_get_master_addr_by_name",
    "sentinel_master",
    "sentinel_masters",
    "sentinel_monitor",
    "sentinel_remove",
    "sentinel_sentinels",
    "sentinel_set",
    "sentinel_slaves",
    "sentinel",
    "set",
    "setbit",
    "setex",
    "setex",
    "setnx",
    "setrange",
    "shutdown",
    "sinter",
    "sinterstore",
    "sismember",
    "slaveof",
    "slowlog_get",
    "slowlog_len",
    "slowlog_reset",
    "smembers",
    "smove",
    "sort",
    "spop",
    "srandmember",
    "srem",
    "sscan_iter",
    "sscan",
    "strlen",
    "substr",
    "sunion",
    "sunionstore",
    "swapdb",
    "time",
    "touch",
    "ttl",
    "type",
    "unlink",
    "unwatch",
    "wait",
    "watch",
    "xack",
    "xadd",
    "xclaim",
    "xdel",
    "xgroup_create",
    "xgroup_delconsumer",
    "xgroup_destroy",
    "xgroup_setid",
    "xinfo_consumers",
    "xinfo_groups",
    "xinfo_stream",
    "xlen",
    "xpending",
    "xrange",
    "xread",
    "xreadgroup",
    "xrevrange",
    "xtrim",
    "zadd",
    "zadd",
    "zcard",
    "zcount",
    "zincrby",
    "zinterstore",
    "zlexcount",
    "zpopmax",
    "zpopmin",
    "zrange",
    "zrangebylex",
    "zrangebyscore",
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
    "zunionstore",
)

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
    port_path_or_id = str(kwargs.get("port") or kwargs.get("path", "unknown"))
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
    for name in _redis_client_methods:
        if hasattr(module, "CoreCommands"):
            if hasattr(module.CoreCommands, name):
                _wrap_Redis_method_wrapper_(module, "CoreCommands", name)
        if hasattr(module, "DataAccessCommands"):
            if hasattr(module.DataAccessCommands, name):
                _wrap_Redis_method_wrapper_(module, "DataAccessCommands", name)


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

    with DatastoreTrace(product="Redis", target=None, operation=operation, host=host, port_path_or_id=port_path_or_id, database_name=db, source=wrapped):
        return wrapped(*args, **kwargs)


def instrument_redis_connection(module):
    wrap_function_wrapper(module, "Connection.send_command", _nr_Connection_send_command_wrapper_)
