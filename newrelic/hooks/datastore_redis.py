import re

from newrelic.agent import (wrap_datastore_trace, wrap_function_wrapper,
        current_transaction, DatastoreTrace)

_redis_client_methods = ('bgrewriteaof', 'bgsave', 'client_kill',
    'client_list', 'client_getname', 'client_setname', 'config_get',
    'config_set', 'config_resetstat', 'config_rewrite', 'dbsize',
    'debug_object', 'echo', 'flushall', 'flushdb', 'info', 'lastsave',
    'object', 'ping', 'save', 'sentinel', 'sentinel_get_master_addr_by_name',
    'sentinel_master', 'sentinel_masters', 'sentinel_monitor',
    'sentinel_remove', 'sentinel_sentinels', 'sentinel_set',
    'sentinel_slaves', 'shutdown', 'slaveof', 'slowlog_get',
    'slowlog_reset', 'time', 'append', 'bitcount', 'bitop', 'bitpos',
    'decr', 'delete', 'dump', 'exists', 'expire', 'expireat', 'get',
    'getbit', 'getrange', 'getset', 'incr', 'incrby', 'incrbyfloat',
    'keys', 'mget', 'mset', 'msetnx', 'move', 'persist', 'pexpire',
    'pexpireat', 'psetex', 'pttl', 'randomkey', 'rename', 'renamenx',
    'restore', 'set', 'setbit', 'setex', 'setnx', 'setrange', 'strlen',
    'substr', 'ttl', 'type', 'watch', 'unwatch', 'blpop', 'brpop',
    'brpoplpush', 'lindex', 'linsert', 'llen', 'lpop', 'lpush',
    'lpushx', 'lrange', 'lrem', 'lset', 'ltrim', 'rpop', 'rpoplpush',
    'rpush', 'rpushx', 'sort', 'scan', 'scan_iter', 'sscan',
    'sscan_iter', 'hscan', 'hscan_inter', 'zscan', 'zscan_iter', 'sadd',
    'scard', 'sdiff', 'sdiffstore', 'sinter', 'sinterstore',
    'sismember', 'smembers', 'smove', 'spop', 'srandmember', 'srem',
    'sunion', 'sunionstore', 'zadd', 'zcard', 'zcount', 'zincrby',
    'zinterstore', 'zlexcount', 'zrange', 'zrangebylex',
    'zrangebyscore', 'zrank', 'zrem', 'zremrangebylex',
    'zremrangebyrank', 'zremrangebyscore', 'zrevrange',
    'zrevrangebyscore', 'zrevrank', 'zscore', 'zunionstore', 'pfadd',
    'pfcount', 'pfmerge', 'hdel', 'hexists', 'hget', 'hgetall',
    'hincrby', 'hincrbyfloat', 'hkeys', 'hlen', 'hset', 'hsetnx',
    'hmset', 'hmget', 'hvals', 'publish', 'eval', 'evalsha',
    'script_exists', 'script_flush', 'script_kill', 'script_load',
    'setex', 'lrem', 'zadd')

def instrument_redis_client(module):
    if hasattr(module, 'StrictRedis'):
        for name in _redis_client_methods:
            if name in vars(module.StrictRedis):
                wrap_datastore_trace(module.StrictRedis, name,
                        product='Redis', target=None, operation=name)

    if hasattr(module, 'Redis'):
        for name in _redis_client_methods:
            if name in vars(module.Redis):
                wrap_datastore_trace(module.Redis, name,
                        product='Redis', target=None, operation=name)

_redis_multipart_commands = set(['client', 'cluster', 'command', 'config',
    'debug', 'sentinel', 'slowlog', 'script'])

_redis_operation_re = re.compile('[-\s]+')

def _nr_Connection_send_command_wrapper_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None or not args:
        return wrapped(*args, **kwargs)

    operation = args[0].strip().lower()

    # Older Redis clients would when sending multi part commands pass
    # them in as separate arguments to send_command(). Need to therefore
    # detect those and grab the next argument from the set of arguments.

    if operation in _redis_multipart_commands and len(args) > 1:
        operation = '%s %s' % (operation, args[1].strip().lower())

    operation = _redis_operation_re.sub('_', operation)

    with DatastoreTrace(transaction, product='Redis', target=None,
            operation=operation):
        return wrapped(*args, **kwargs)

def instrument_redis_connection(module):
    wrap_function_wrapper(module, 'Connection.send_command',
            _nr_Connection_send_command_wrapper_)
