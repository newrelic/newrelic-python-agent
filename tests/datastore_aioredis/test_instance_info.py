# Copyright 2010 New Relic, Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from inspect import isawaitable
import pytest

from newrelic.hooks.datastore_aioredis import _conn_attrs_to_dict, _instance_info
from conftest import aioredis, AIOREDIS_VERSION, SKIPIF_AIOREDIS_V1

_instance_info_tests = [
    ({}, ("localhost", "6379", "0")),
    ({"host": None}, ("localhost", "6379", "0")),
    ({"host": ""}, ("localhost", "6379", "0")),
    ({"db": None}, ("localhost", "6379", "0")),
    ({"db": ""}, ("localhost", "6379", "0")),
    ({"host": "127.0.0.1", "port": 1234, "db": 2}, ("127.0.0.1", "1234", "2")),
]


if AIOREDIS_VERSION >= (2, 0):
    clients = [aioredis.Redis, aioredis.StrictRedis]
    class DisabledConnection(aioredis.Connection):
        @staticmethod
        async def connect(*args, **kwargs):
            pass
    
        async def can_read_destructive(self, *args, **kwargs):
            return False



    class DisabledUnixConnection(aioredis.UnixDomainSocketConnection, DisabledConnection):
        pass

else:
    clients = []
    DisabledConnection, DisabledUnixConnection = None, None



@SKIPIF_AIOREDIS_V1
@pytest.mark.parametrize("client_cls", clients)
@pytest.mark.parametrize("kwargs,expected", _instance_info_tests)
def test_strict_redis_client_instance_info(client_cls, kwargs, expected, loop):
    r = client_cls(**kwargs)
    if isawaitable(r):
        r = loop.run_until_complete(r)
    conn_kwargs = r.connection_pool.connection_kwargs
    assert _instance_info(conn_kwargs) == expected


@SKIPIF_AIOREDIS_V1
@pytest.mark.parametrize("client_cls", clients)
@pytest.mark.parametrize("kwargs,expected", _instance_info_tests)
def test_strict_redis_connection_instance_info(client_cls, kwargs, expected, loop):
    r = client_cls(**kwargs)
    if isawaitable(r):
        r = loop.run_until_complete(r)
    r.connection_pool.connection_class = DisabledConnection
    connection = loop.run_until_complete(r.connection_pool.get_connection("SELECT"))
    try:
        conn_kwargs = _conn_attrs_to_dict(connection)
        assert _instance_info(conn_kwargs) == expected
    finally:
        loop.run_until_complete(r.connection_pool.release(connection))


_instance_info_from_url_tests = [
    (("redis://localhost:1234/",), {}, ("localhost", "1234", "0")),
    (("redis://localhost:1234",), {}, ("localhost", "1234", "0")),
    (("redis://user:password@localhost:6379",), {}, ("localhost", "6379", "0")),
    (("redis://localhost:6379/2",), {}, ("localhost", "6379", "2")),
    (("redis://localhost:6379",), {"db": 2}, ("localhost", "6379", "2")),
    (("redis://@127.0.0.1:6379",), {}, ("127.0.0.1", "6379", "0")),
    (("redis://:1234/",), {}, ("localhost", "1234", "0")),
    (("redis://@:1234/",), {}, ("localhost", "1234", "0")),
    (("redis://localhost:1234/garbage",), {}, ("localhost", "1234", "0")),
    (("redis://127.0.0.1",), {}, ("127.0.0.1", "6379", "0")),
    (("rediss://localhost:6379/2/",), {}, ("localhost", "6379", "2")),          # rediss: Not a typo
    (("redis://localhost:6379",), {"host": "someotherhost"}, ("localhost", "6379", "0")),
    (("redis://localhost:6379/2",), {"db": 3}, ("localhost", "6379", "2")),
    (("redis://localhost:6379/2/?db=111",), {}, ("localhost", "6379", "111")),
    (("redis://localhost:6379?db=2",), {}, ("localhost", "6379", "2")),
    (("redis://localhost:6379/2?db=111",), {}, ("localhost", "6379", "111")),
    (("unix:///path/to/socket.sock",), {}, ("localhost", "/path/to/socket.sock", "0")),
    (("unix:///path/to/socket.sock?db=2",), {}, ("localhost", "/path/to/socket.sock", "2")),
    (("unix:///path/to/socket.sock",), {"db": 2}, ("localhost", "/path/to/socket.sock", "2")),
]


@SKIPIF_AIOREDIS_V1
@pytest.mark.parametrize("client_cls", clients)
@pytest.mark.parametrize("args,kwargs,expected", _instance_info_from_url_tests)
def test_strict_redis_client_from_url(client_cls, args, kwargs, expected):
    r = client_cls.from_url(*args, **kwargs)
    conn_kwargs = r.connection_pool.connection_kwargs
    assert _instance_info(conn_kwargs) == expected


@SKIPIF_AIOREDIS_V1
@pytest.mark.parametrize("client_cls", clients)
@pytest.mark.parametrize("args,kwargs,expected", _instance_info_from_url_tests)
def test_strict_redis_connection_from_url(client_cls, args, kwargs, expected, loop):
    r = client_cls.from_url(*args, **kwargs)
    if r.connection_pool.connection_class in (aioredis.Connection, aioredis.connection.SSLConnection):
        r.connection_pool.connection_class = DisabledConnection
    elif r.connection_pool.connection_class is aioredis.UnixDomainSocketConnection:
        r.connection_pool.connection_class = DisabledUnixConnection
    else:
        assert False, r.connection_pool.connection_class

    connection = loop.run_until_complete(r.connection_pool.get_connection("SELECT"))
    try:
        conn_kwargs = _conn_attrs_to_dict(connection)
        assert _instance_info(conn_kwargs) == expected
    finally:
        loop.run_until_complete(r.connection_pool.release(connection))
