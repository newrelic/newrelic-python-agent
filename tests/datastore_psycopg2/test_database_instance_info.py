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
from newrelic.hooks.database_psycopg2 import (instance_info, _add_defaults,
        _parse_connect_params)

def test_kwargs():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': 1234})
    output = _parse_connect_params(*connect_params)
    assert output == ('1.2.3.4', None, '1234', 'foo')

def test_arg_str():
    connect_params = (("host=foobar port=9876",), {})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', None, '9876', None)

def test_bind_dsn():
    connect_params = ((), {'dsn': 'host=foobar port=9876'})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', None, '9876', None)

def test_bind_dsn_ignore_kwargs():
    connect_params = ((), {'dsn': "host=foobar", 'port': 1234})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', None, None, None)

def test_kwargs_str_for_port():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': '1234'})
    output = _parse_connect_params(*connect_params)
    assert output == ('1.2.3.4', None, '1234', 'foo')

def test_arg_str_missing_port():
    connect_params = (("host=foobar",), {})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', None, None, None)

def test_arg_str_multiple_host():
    connect_params = (("host=foobar host=barbaz",), {})
    output = _parse_connect_params(*connect_params)
    assert output == ('barbaz', None, None, None)

def test_arg_str_multiple_port():
    connect_params = (("port=5555 port=7777",), {})
    output = _parse_connect_params(*connect_params)
    assert output == (None, None, '7777', None)

def test_arg_str_missing_host():
    connect_params = (("port=5555",), {})
    output = _parse_connect_params(*connect_params)
    assert output == (None, None, '5555', None)

def test_arg_str_missing_host_and_port():
    connect_params = (("nothing=here",), {})
    output = _parse_connect_params(*connect_params)
    assert output == (None, None, None, None)

def test_malformed_arg_str():
    connect_params = (("this_is_malformed",), {})
    output = _parse_connect_params(*connect_params)
    assert output == ('unknown', 'unknown', 'unknown', 'unknown')

def test_str_in_port_arg_str():
    connect_params = (("port=foobar",), {})
    output = _parse_connect_params(*connect_params)
    assert output == (None, None, 'foobar', None)

def test_host_and_hostaddr_in_arg_str():
    connect_params = (("host=foobar hostaddr=1.2.3.4",), {})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', '1.2.3.4', None, None)

def test_host_and_hostaddr_in_kwarg():
    connect_params = ((), {'host':'foobar', 'hostaddr':'1.2.3.4'})
    output = _parse_connect_params(*connect_params)
    assert output == ('foobar', '1.2.3.4', None, None)

def test_only_hostaddr_in_kwarg():
    connect_params = ((), {'hostaddr':'1.2.3.4'})
    output = _parse_connect_params(*connect_params)
    assert output == (None, '1.2.3.4', None, None)

def test_only_hostaddr_in_arg_str():
    connect_params = (("hostaddr=1.2.3.4",), {})
    output = _parse_connect_params(*connect_params)
    assert output == (None, '1.2.3.4', None, None)

def test_env_var_default_host(monkeypatch):
    monkeypatch.setenv('PGHOST', 'envfoo')
    output = _add_defaults(None, None, '1234', 'foo')
    assert output == ('envfoo', '1234', 'foo')

def test_env_var_default_hostaddr(monkeypatch):
    monkeypatch.setenv('PGHOSTADDR', '1.2.3.4')
    output = _add_defaults(None, None, '1234', 'foo')
    assert output == ('1.2.3.4', '1234', 'foo')

def test_env_var_default_database(monkeypatch):
    monkeypatch.setenv('PGDATABASE', 'dbenvfoo')
    output = _add_defaults('foo', None, '1234', None)
    assert output == ('foo', '1234', 'dbenvfoo')

def test_env_var_default_port(monkeypatch):
    monkeypatch.setenv('PGPORT', '9999')
    output = _add_defaults('foo', None, None, 'bar')
    assert output == ('foo', '9999', 'bar')

@pytest.mark.parametrize('connect_params,expected', [
    ((('postgresql://',), {}),
        ('localhost', 'default', 'default')),
    ((('postgresql://localhost',), {}),
        ('localhost', '5432', 'default')),
    ((('postgresql://localhost:5433',), {}),
        ('localhost', '5433', 'default')),
    ((('postgresql://localhost/mydb',), {}),
        ('localhost', '5432', 'mydb')),
    ((('postgresql://user@localhost',), {}),
        ('localhost', '5432', 'default')),
    ((('postgresql://user:secret@localhost',), {}),
        ('localhost', '5432', 'default')),
    ((('postgresql://[2001:db8::1234]/database',), {}),
        ('2001:db8::1234', '5432', 'database')),
    ((('postgresql://[2001:db8::1234]:2222/database',), {}),
        ('2001:db8::1234', '2222', 'database')),
    ((('postgresql:///dbname?host=/var/lib/postgresql',), {}),
        ('localhost', '/var/lib/postgresql/.s.PGSQL.5432', 'dbname')),
    ((('postgresql://%2Fvar%2Flib%2Fpostgresql/dbname',), {}),
        ('localhost', '/var/lib/postgresql/.s.PGSQL.5432', 'dbname')),
    ((('postgresql://other@localhost/otherdb?c=10&a=myapp',), {}),
        ('localhost', '5432', 'otherdb')),
    ((('postgresql:///',), {}),
        ('localhost', 'default', 'default')),
    ((('postgresql:///dbname?host=foo',), {}),
        ('foo', '5432', 'dbname')),
    ((('postgresql:///dbname?port=1234',), {}),
        ('localhost', 'default', 'dbname')),
    ((('postgresql:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234', 'dbname')),
    ((('postgres:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234', 'dbname')),
    ((('postgres://localhost:5444/blah?host=::1',), {}),
        ('::1', '5444', 'blah')),
    ((('postgresql:///dbname?host=foo&port=1234&host=bar',), {}),
        ('bar', '1234', 'dbname')),
    ((('postgresql://%2Ftmp:1234',), {}),
        ('localhost', '/tmp/.s.PGSQL.1234', 'default')),
    ((('postgresql:///foo?dbname=bar',), {}),
        ('localhost', 'default', 'bar')),
    ((('postgresql://example.com/foo?hostaddr=1.2.3.4&host=bar',), {}),
        ('1.2.3.4', '5432', 'foo')),
])
def test_uri(connect_params, expected):
    output = instance_info(*connect_params)
    assert output == expected

@pytest.mark.parametrize('connect_params,expected', [
    ((('postgresql://user:password@/?dbname=bar',), {}),
        ('localhost', 'default', 'bar')),
    ((('postgresql://user:pass@host/?dbname=bar',), {}),
        ('host', '5432', 'bar')),
    ((('postgresql://user:password@@/?dbname=bar',), {}),
        ('localhost', 'default', 'bar')),
    ((('postgresql://@',), {}),
        ('localhost', 'default', 'default')),
    ((('postgresql://@@localhost',), {}),
        ('localhost', '5432', 'default')),
])
def test_security_sensitive_uri(connect_params, expected):
    output = instance_info(*connect_params)
    assert output == expected

def test_bad_uri():
    connect_params = (("blah:///foo",), {})
    output = instance_info(*connect_params)
    assert output == ('unknown', 'unknown', 'unknown')

_test_add_defaults = [

    # TCP/IP

    [('otherhost.com', None, '8888', 'foobar'), ('otherhost.com', '8888', 'foobar')],
    [('otherhost.com', None, None, 'foobar'), ('otherhost.com', '5432', 'foobar')],
    [('localhost', None, '8888', 'foobar'), ('localhost', '8888', 'foobar')],
    [('localhost', None, None, 'foobar'), ('localhost', '5432', 'foobar')],
    [('127.0.0.1', None, '8888', 'foobar'), ('127.0.0.1', '8888', 'foobar')],
    [('127.0.0.1', None, None, 'foobar'), ('127.0.0.1', '5432', 'foobar')],
    [('::1', None, '8888', None), ('::1', '8888', 'default')],
    [('::1', None, None, None), ('::1', '5432', 'default')],
    [('::1', None, None, ''), ('::1', '5432', 'default')],

    # Unix Domain Socket

    [(None, None, None, None), ('localhost', 'default', 'default')],
    [(None, None, '5432', None), ('localhost', 'default', 'default')],
    [(None, None, '8888', None), ('localhost', 'default', 'default')],
    [('/tmp', None, None, 'cat'), ('localhost', '/tmp/.s.PGSQL.5432', 'cat')],
    [('/tmp', None, '5432', 'dog'), ('localhost', '/tmp/.s.PGSQL.5432', 'dog')],
    [('/tmp', None, '8888', 'db'), ('localhost', '/tmp/.s.PGSQL.8888', 'db')],
]

@pytest.mark.parametrize('host_port,expected', _test_add_defaults)
def test_add_defaults(host_port, expected):
    actual = _add_defaults(*host_port)
    assert actual == expected
