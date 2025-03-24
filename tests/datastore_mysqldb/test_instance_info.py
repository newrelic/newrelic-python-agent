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

from newrelic.hooks.database_mysqldb import instance_info

_instance_info_tests = [
    # test parameter resolution
    ((), {}, ('localhost', 'default', 'unknown')),
    ((), {'port': 1234}, ('localhost', 'default', 'unknown')),
    ((), {'host':'localhost', 'port': 1234},
            ('localhost', 'default', 'unknown')),
    ((), {'unix_socket': '/tmp/foo'}, ('localhost', '/tmp/foo', 'unknown')),
    ((), {'host': '1.2.3.4'}, ('1.2.3.4', '3306', 'unknown')),
    ((), {'host': '1.2.3.4', 'port': 1234}, ('1.2.3.4', '1234', 'unknown')),
    ((), {'host': '1.2.3.4', 'port': 1234, 'unix_socket': '/foo'},
            ('1.2.3.4', '1234', 'unknown')),
    ((), {'db': 'foobar', 'unix_socket':'/tmp/mysql.sock'},
            ('localhost', '/tmp/mysql.sock', 'foobar')),
    ((), {'db': 'foobar'}, ('localhost', 'default', 'foobar')),
    ((), {'host': '1.2.3.4', 'port': 0}, ('1.2.3.4', '3306', 'unknown')),
    ((), {'host': '', 'port': 1234}, ('localhost', 'default', 'unknown')),
    ((), {'db':''}, ('localhost', 'default', 'unknown')),

    # test arg binding
    (('1.2.3.4',), {}, ('1.2.3.4', '3306', 'unknown')),
    (('1.2.3.4', None, None, None, 1234), {}, ('1.2.3.4', '1234', 'unknown')),
    (('1.2.3.4', None, None, 'dbfoo'), {}, ('1.2.3.4', '3306', 'dbfoo')),
    ((None, None, None, None, None, '/foo'), {}, ('localhost', '/foo', 'unknown')),
]

@pytest.mark.parametrize('args,kwargs,expected', _instance_info_tests)
def test_mysqldb_instance_info(args, kwargs, expected):
    connect_params = (args, kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_env_var_default_tcp_port(monkeypatch):
    monkeypatch.setenv('MYSQL_TCP_PORT', '1234')
    kwargs = {'host': '1.2.3.4'}
    expected = ('1.2.3.4', '1234', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_override_env_var_tcp_port(monkeypatch):
    monkeypatch.setenv('MYSQL_TCP_PORT', '1234')
    kwargs = {'host': '1.2.3.4', 'port': 9876}
    expected = ('1.2.3.4', '9876', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_env_var_default_unix_port(monkeypatch):
    monkeypatch.setenv('MYSQL_UNIX_PORT', '/foo/bar')
    kwargs = {}
    expected = ('localhost', '/foo/bar', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_override_env_var_unix_port(monkeypatch):
    monkeypatch.setenv('MYSQL_UNIX_PORT', '/bar/baz')
    kwargs = {'unix_socket': 'foobar'}
    expected = ('localhost', 'foobar', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_default_file():
    kwargs = {'read_default_group': 'foobar'}
    expected = ('default', 'unknown', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_default_group():
    kwargs = {'read_default_group': 'foobar'}
    expected = ('default', 'unknown', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_default_precedence():
    kwargs = {'port': 1234, 'host': '1.2.3.4', 'read_default_group': 'foobar'}
    expected = ('1.2.3.4', '1234', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_localhost_cnf(monkeypatch):
    monkeypatch.setenv('MYSQL_UNIX_PORT', '/foo/bar')
    kwargs = {'host': 'localhost', 'read_default_group': 'foobar'}
    expected = ('localhost', 'unknown', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_explicit_host_cnf(monkeypatch):
    monkeypatch.setenv('MYSQL_TCP_PORT', '1234')
    kwargs = {'host': '1.2.3.4', 'read_default_group': 'foobar'}
    expected = ('1.2.3.4', 'unknown', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected

def test_mysql_host_env_ignored(monkeypatch):
    monkeypatch.setenv('MYSQL_HOST', 'FOOBAR')
    kwargs = {}
    expected = ('localhost', 'default', 'unknown')

    connect_params = ((), kwargs)
    output = instance_info(*connect_params)
    assert output == expected
