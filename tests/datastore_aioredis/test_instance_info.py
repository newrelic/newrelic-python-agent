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
import aioredis

from newrelic.hooks.datastore_aioredis import _conn_attrs_to_dict, _instance_info
from testing_support.fixture.event_loop import event_loop as loop

_instance_info_tests = [
    ({}, ("localhost", "6379", "0")),
    ({"host": None}, ("localhost", "6379", "0")),
    ({"host": ""}, ("localhost", "6379", "0")),
    ({"db": None}, ("localhost", "6379", "0")),
    ({"db": ""}, ("localhost", "6379", "0")),
    ({"host": "127.0.0.1", "port": 1234, "db": 2}, ("127.0.0.1", "1234", "2")),
]

redis_client = aioredis.Redis
strict_redis_client = aioredis.StrictRedis


class DisabledConnection(aioredis.Connection):
    @staticmethod
    async def connect(*args, **kwargs):
        pass


class DisabledUnixConnection(aioredis.UnixDomainSocketConnection, DisabledConnection):
    pass


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
@pytest.mark.parametrize("kwargs,expected", _instance_info_tests)
def test_strict_redis_client_instance_info(client, kwargs, expected):
    r = client(**kwargs)
    conn_kwargs = r.connection_pool.connection_kwargs
    assert _instance_info(conn_kwargs) == expected


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
@pytest.mark.parametrize("kwargs,expected", _instance_info_tests)
def test_strict_redis_connection_instance_info(client, kwargs, expected, loop):
    r = client(**kwargs)
    r.connection_pool.connection_class = DisabledConnection
    connection = loop.run_until_complete(r.connection_pool.get_connection("SELECT"))
    try:
        conn_kwargs = _conn_attrs_to_dict(connection)
        assert _instance_info(conn_kwargs) == expected
    finally:
        r.connection_pool.release(connection)


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


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
@pytest.mark.parametrize("args,kwargs,expected", _instance_info_from_url_tests)
def test_strict_redis_client_from_url(client, args, kwargs, expected):
    r = client.from_url(*args, **kwargs)
    conn_kwargs = r.connection_pool.connection_kwargs
    assert _instance_info(conn_kwargs) == expected


@pytest.mark.parametrize("client", (redis_client, strict_redis_client))
@pytest.mark.parametrize("args,kwargs,expected", _instance_info_from_url_tests)
def test_strict_redis_connection_from_url(client, args, kwargs, expected, loop):
    r = client.from_url(*args, **kwargs)
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
        r.connection_pool.release(connection)
