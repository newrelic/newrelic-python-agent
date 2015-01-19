from newrelic.agent import wrap_datastore_trace

_methods_1 = ['bgrewriteaof', 'bgsave', 'client_kill', 'client_list',
    'client_getname', 'client_setname', 'config_get', 'config_set',
    'config_resetstat', 'config_rewrite', 'dbsize', 'debug_object', 'echo',
    'flushall', 'flushdb', 'info', 'lastsave', 'object', 'ping', 'save',
    'sentinel', 'sentinel_get_master_addr_by_name', 'sentinel_master',
    'sentinel_masters', 'sentinel_monitor', 'sentinel_remove',
    'sentinel_sentinels', 'sentinel_set', 'sentinel_slaves', 'shutdown',
    'slaveof', 'slowlog_get', 'slowlog_reset', 'time', 'append',
    'bitcount', 'bitop', 'bitpos', 'decr', 'delete', 'dump', 'exists',
    'expire', 'expireat', 'get', 'getbit', 'getrange', 'getset', 'incr',
    'incrby', 'incrbyfloat', 'keys', 'mget', 'mset', 'msetnx', 'move',
    'persist', 'pexpire', 'pexpireat', 'psetex', 'pttl', 'randomkey',
    'rename', 'renamenx', 'restore', 'set', 'setbit', 'setex', 'setnx',
    'setrange', 'strlen', 'substr', 'ttl', 'type', 'watch', 'unwatch',
    'blpop', 'brpop', 'brpoplpush', 'lindex', 'linsert', 'llen', 'lpop',
    'lpush', 'lpushx', 'lrange', 'lrem', 'lset', 'ltrim', 'rpop',
    'rpoplpush', 'rpush', 'rpushx', 'sort', 'scan', 'scan_iter', 'sscan',
    'sscan_iter', 'hscan', 'hscan_inter', 'zscan', 'zscan_iter', 'sadd',
    'scard', 'sdiff', 'sdiffstore', 'sinter', 'sinterstore', 'sismember',
    'smembers', 'smove', 'spop', 'srandmember', 'srem', 'sunion',
    'sunionstore', 'zadd', 'zcard', 'zcount', 'zincrby', 'zinterstore',
    'zlexcount', 'zrange', 'zrangebylex', 'zrangebyscore', 'zrank', 'zrem',
    'zremrangebylex', 'zremrangebyrank', 'zremrangebyscore', 'zrevrange',
    'zrevrangebyscore', 'zrevrank', 'zscore', 'zunionstore', 'pfadd',
    'pfcount', 'pfmerge', 'hdel', 'hexists', 'hget', 'hgetall', 'hincrby',
    'hincrbyfloat', 'hkeys', 'hlen', 'hset', 'hsetnx', 'hmset', 'hmget',
    'hvals', 'publish', 'eval', 'evalsha', 'script_exists', 'script_flush',
    'script_kill', 'script_load']

_methods_2 = ['setex', 'lrem', 'zadd']

def instrument_redis_client(module):
    if hasattr(module, 'StrictRedis'):
        for method in _methods_1:
            if hasattr(module.StrictRedis, method):
                wrap_datastore_trace(module, 'StrictRedis.%s' % method,
                        product='Redis', target=None, operation=method)
    else:
        for method in _methods_1:
            if hasattr(module.Redis, method):
                wrap_datastore_trace(module, 'Redis.%s' % method,
                        product='Redis', target=None, operation=method)

    for method in _methods_2:
        if hasattr(module.Redis, method):
            wrap_datastore_trace(module, 'Redis.%s' % method,
                    product='Redis', target=None, operation=method)
