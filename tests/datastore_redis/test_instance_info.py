import pytest
import redis

from newrelic.hooks.datastore_redis import (_client_instance_info,
        _connection_instance_info)

REDIS_PY_VERSION = redis.VERSION

_instance_info_tests = [
    ((), {}, ('localhost', '6379', '0')),
    ((), {'host': '127.0.0.1', 'port': 1234, 'db': 2}, ('127.0.0.1', '1234', '2')),
    (('127.0.0.1', 1234, 2), {}, ('127.0.0.1', '1234', '2')),
]

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_redis_client_instance_info(args, kwargs, expected):
    r = redis.Redis(*args, **kwargs)
    assert _client_instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_strict_redis_client_instance_info(args, kwargs, expected):
    r = redis.StrictRedis(*args, **kwargs)
    assert _client_instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_redis_connection_instance_info(args, kwargs, expected):
    r = redis.Redis(*args, **kwargs)
    connection = r.connection_pool.get_connection('SELECT')
    try:
        assert _connection_instance_info(connection) == expected
    finally:
        r.connection_pool.release(connection)

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_strict_redis_connection_instance_info(args, kwargs, expected):
    r = redis.StrictRedis(*args, **kwargs)
    connection = r.connection_pool.get_connection('SELECT')
    try:
        assert _connection_instance_info(connection) == expected
    finally:
        r.connection_pool.release(connection)

_instance_info_from_url_tests = [
    (('redis://localhost:1234/',), {}, ('localhost', '1234', '0')),
    (('redis://localhost:1234',), {}, ('localhost', '1234', '0')),
    (('redis://user:password@localhost:6379',), {}, ('localhost', '6379', '0')),
    (('redis://localhost:6379/2',), {}, ('localhost', '6379', '2')),
    (('redis://localhost:6379',), {'db': 2}, ('localhost', '6379', '2')),
    (('redis://@127.0.0.1:6379',), {}, ('127.0.0.1', '6379', '0')),
    (('redis://:1234/',), {}, ('localhost', '1234', '0')),
    (('redis://@:1234/',), {}, ('localhost', '1234', '0')),
    (('redis://localhost:1234/garbage',), {}, ('localhost', '1234', '0')),
]

if REDIS_PY_VERSION >= (2, 7, 5):
    _instance_info_from_url_tests.append(
        (('redis://127.0.0.1',), {}, ('127.0.0.1', '6379', '0'))
    )

if REDIS_PY_VERSION >= (2, 10):
    _instance_info_from_url_tests.extend([
        (('rediss://localhost:6379/2/',), {}, ('localhost', '6379', '2')),
        (('redis://localhost:6379',), {'host': 'someotherhost'},
                ('localhost', '6379', '0')),
        (('redis://localhost:6379/2',), {'db': 3}, ('localhost', '6379', '2')),
        (('redis://localhost:6379/2/?db=111',), {}, ('localhost', '6379', '111')),
        (('redis://localhost:6379?db=2',), {}, ('localhost', '6379', '2')),
        (('redis://localhost:6379/2?db=111',), {},
                ('localhost', '6379', '111')),

        (('unix:///path/to/socket.sock',), {},
                ('localhost', '/path/to/socket.sock', '0')),
        (('unix:///path/to/socket.sock?db=2',), {},
                ('localhost', '/path/to/socket.sock', '2')),
        (('unix:///path/to/socket.sock',), {'db': 2},
                ('localhost', '/path/to/socket.sock', '2')),
    ])

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 6),
        reason='from_url not yet implemented in this redis-py version')
@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_redis_client_from_url(args, kwargs, expected):
    r = redis.Redis.from_url(*args, **kwargs)
    assert _client_instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_strict_redis_client_from_url(args, kwargs, expected):
    r = redis.StrictRedis.from_url(*args, **kwargs)
    assert _client_instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_redis_connection_from_url(args, kwargs, expected):
    r = redis.Redis.from_url(*args, **kwargs)
    connection = r.connection_pool.get_connection('SELECT')
    try:
        assert _connection_instance_info(connection) == expected
    finally:
        r.connection_pool.release(connection)

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 6),
        reason='from_url not yet implemented in this redis-py version')
@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_strict_redis_connection_from_url(args, kwargs, expected):
    r = redis.StrictRedis.from_url(*args, **kwargs)
    connection = r.connection_pool.get_connection('SELECT')
    try:
        assert _connection_instance_info(connection) == expected
    finally:
        r.connection_pool.release(connection)
