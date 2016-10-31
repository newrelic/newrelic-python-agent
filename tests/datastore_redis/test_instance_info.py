import pytest
import redis

from newrelic.hooks.datastore_redis import _instance_info

REDIS_PY_VERSION = redis.VERSION

_instance_info_tests = [
    ((), {}, ('localhost', '6379', '0')),
    ((), {'host': None}, ('localhost', '6379', '0')),
    ((), {'host': ''}, ('localhost', '6379', '0')),
    ((), {'db': None}, ('localhost', '6379', '0')),
    ((), {'db': ''}, ('localhost', '6379', '0')),
    ((), {'host': '127.0.0.1', 'port': 1234, 'db': 2}, ('127.0.0.1', '1234', '2')),
    (('127.0.0.1', 1234, 2), {}, ('127.0.0.1', '1234', '2')),
]

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_redis_instance_info(args, kwargs, expected):
    r = redis.Redis(*args, **kwargs)
    assert _instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_strict_redis_instance_info(args, kwargs, expected):
    r = redis.StrictRedis(*args, **kwargs)
    assert _instance_info(r) == expected

_instance_info_from_url_tests_redis = [
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
    _instance_info_from_url_tests_redis.append(
        (('redis://127.0.0.1',), {}, ('127.0.0.1', '6379', '0'))
    )

if REDIS_PY_VERSION >= (2, 10):
    _instance_info_from_url_tests_redis.extend([
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
        (('unix:///path/to/socket.sock?smellysocks=2',), {},
                ('localhost', '/path/to/socket.sock', '0')),
    ])

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 6),
        reason='from_url not yet implemented in this redis-py version')
@pytest.mark.parametrize('args,kwargs,expected',
        _instance_info_from_url_tests_redis)
def test_redis_from_url_redis(args, kwargs, expected):
    r = redis.Redis.from_url(*args, **kwargs)
    assert _instance_info(r) == expected

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 6),
        reason='from_url not yet implemented in this redis-py version')
@pytest.mark.parametrize('args,kwargs,expected',
        _instance_info_from_url_tests_redis)
def test_strict_redis_from_url_redis(args, kwargs, expected):
    r = redis.StrictRedis.from_url(*args, **kwargs)
    assert _instance_info(r) == expected
