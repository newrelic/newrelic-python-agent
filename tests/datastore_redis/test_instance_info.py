import pytest
import redis

from newrelic.hooks.datastore_redis import _instance_info

_instance_info_tests = [
    ((), {}, ('localhost', 6379, 0)),
    ((), {'host': '127.0.0.1', 'port': 1234, 'db': 2}, ('127.0.0.1', 1234, 2)),
    (('127.0.0.1', 1234, 2), {}, ('127.0.0.1', 1234, 2)),
]

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_redis_instance_info(args, kwargs, expected):
    r = redis.Redis(*args, **kwargs)
    assert _instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_strict_redis_instance_info(args, kwargs, expected):
    r = redis.StrictRedis(*args, **kwargs)
    assert _instance_info(r) == expected

_instance_info_from_url_tests = [
    (('redis://127.0.0.1',), {}, ('127.0.0.1', 6379, 0)),
    (('redis://localhost:1234/',), {}, ('localhost', 1234, 0)),
    (('redis://user:password@localhost',), {}, ('localhost', 6379, 0)),
    (('rediss://localhost/2/',), {}, ('localhost', 6379, 2)),
    (('redis://localhost/2',), {}, ('localhost', 6379, 2)),
    (('redis://localhost?db=2',), {}, ('localhost', 6379, 2)),
    (('redis://localhost',), {'db': 2}, ('localhost', 6379, 2)),
    (('redis://localhost/2',), {'db': 3}, ('localhost', 6379, 2)),
    (('redis://localhost',), {'host': 'someotherhost'}, ('localhost', 6379, 0)),
    (('redis://localhost/2/?db=111',), {}, ('localhost', 6379, 111)),
    (('redis://@127.0.0.1',), {}, ('127.0.0.1', 6379, 0)),
    (('redis://:1234/',), {}, ('localhost', 1234, 0)),
    (('redis://@:1234/',), {}, ('localhost', 1234, 0)),

    (('unix:///path/to/socket.sock',), {},
            ('localhost', '/path/to/socket.sock', 0)),
    (('unix:///path/to/socket.sock?db=2',), {},
            ('localhost', '/path/to/socket.sock', 2)),
    (('unix:///path/to/socket.sock?smellysocks=2',), {},
            ('localhost', '/path/to/socket.sock', 0)),
]

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_redis_from_url(args, kwargs, expected):
    r = redis.Redis.from_url(*args, **kwargs)
    assert _instance_info(r) == expected

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_from_url_tests)
def test_strict_redis_from_url(args, kwargs, expected):
    r = redis.StrictRedis.from_url(*args, **kwargs)
    assert _instance_info(r) == expected
