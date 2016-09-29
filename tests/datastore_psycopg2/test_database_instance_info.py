import pytest
from newrelic.hooks.database_psycopg2 import instance_info, _add_defaults

def test_kwargs():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': 1234})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', '1234', 'foo')

def test_arg_str():
    connect_params = (("host=foobar port=9876",), {})
    output = instance_info(*connect_params)
    assert output == ('foobar', '9876', None)

def test_bind_dsn():
    connect_params = ((), {'dsn': 'host=foobar port=9876'})
    output = instance_info(*connect_params)
    assert output == ('foobar', '9876', None)

def test_bind_dsn_ignore_kwargs():
    connect_params = ((), {'dsn': "host=foobar", 'port': 1234})
    output = instance_info(*connect_params)
    assert output == ('foobar', None, None)

def test_kwargs_str_for_port():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': '1234'})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', '1234', 'foo')

def test_arg_str_missing_port():
    connect_params = (("host=foobar",), {})
    output = instance_info(*connect_params)
    assert output == ('foobar', None, None)

def test_arg_str_multiple_host():
    connect_params = (("host=foobar host=barbaz",), {})
    output = instance_info(*connect_params)
    assert output == ('barbaz', None, None)

def test_arg_str_multiple_port():
    connect_params = (("port=5555 port=7777",), {})
    output = instance_info(*connect_params)
    assert output == (None, '7777', None)

def test_arg_str_missing_host():
    connect_params = (("port=5555",), {})
    output = instance_info(*connect_params)
    assert output == (None, '5555', None)

def test_arg_str_missing_host_and_port():
    connect_params = (("nothing=here",), {})
    output = instance_info(*connect_params)
    assert output == (None, None, None)

def test_malformed_arg_str():
    connect_params = (("this_is_malformed",), {})
    output = instance_info(*connect_params)
    assert output == ('unknown', 'unknown', 'unknown')

def test_str_in_port_arg_str():
    connect_params = (("port=foobar",), {})
    output = instance_info(*connect_params)
    assert output == (None, 'foobar', None)

def test_host_and_hostaddr_in_arg_str():
    connect_params = (("host=foobar hostaddr=1.2.3.4",), {})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', None, None)

def test_host_and_hostaddr_in_kwarg():
    connect_params = ((), {'host':'foobar', 'hostaddr':'1.2.3.4'})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', None, None)

def test_only_hostaddr_in_kwarg():
    connect_params = ((), {'hostaddr':'1.2.3.4'})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', None, None)

def test_only_hostaddr_in_arg_str():
    connect_params = (("hostaddr=1.2.3.4",), {})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', None, None)

def test_env_var_default_host(monkeypatch):
    monkeypatch.setenv('PGHOST', 'envfoo')
    output = _add_defaults(None, '1234', 'foo')
    assert output == ('envfoo', '1234', 'foo')

def test_env_var_default_database(monkeypatch):
    monkeypatch.setenv('PGDATABASE', 'dbenvfoo')
    output = _add_defaults('foo', '1234', None)
    assert output == ('foo', '1234', 'dbenvfoo')

def test_env_var_default_port(monkeypatch):
    monkeypatch.setenv('PGPORT', '9999')
    output = _add_defaults('foo', None, 'bar')
    assert output == ('foo', '9999', 'bar')

@pytest.mark.parametrize('connect_params,expected', [
    ((('postgresql://',), {}),
        (None, None, None)),
    ((('postgresql://localhost',), {}),
        ('localhost', None, None)),
    ((('postgresql://localhost:5433',), {}),
        ('localhost', '5433', None)),
    ((('postgresql://localhost/mydb',), {}),
        ('localhost', None, 'mydb')),
    ((('postgresql://user@localhost',), {}),
        ('localhost', None, None)),
    ((('postgresql://user:secret@localhost',), {}),
        ('localhost', None, None)),
    ((('postgresql://[2001:db8::1234]/database',), {}),
        ('[2001:db8::1234]', None, 'database')),
    ((('postgresql://[2001:db8::1234]:2222/database',), {}),
        ('[2001:db8::1234]', '2222', 'database')),
    ((('postgresql:///dbname?host=/var/lib/postgresql',), {}),
        ('/var/lib/postgresql',  None, 'dbname')),
    ((('postgresql://%2Fvar%2Flib%2Fpostgresql/dbname',), {}),
        ('/var/lib/postgresql',  None, 'dbname')),
    ((('postgresql://other@localhost/otherdb?c=10&a=myapp',), {}),
        ('localhost', None, 'otherdb')),
    ((('postgresql:///',), {}),
        (None, None, None)),
    ((('postgresql:///dbname?host=foo',), {}),
        ('foo', None, 'dbname')),
    ((('postgresql:///dbname?port=1234',), {}),
        (None, '1234', 'dbname')),
    ((('postgresql:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234', 'dbname')),
    ((('postgres:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234', 'dbname')),
    ((('postgres://localhost:5444/blah?host=::1',), {}),
        ('::1', '5444', 'blah')),
    ((('postgresql:///dbname?host=foo&port=1234&host=bar',), {}),
        ('bar', '1234', 'dbname')),
    ((('postgresql://%2Ftmp:1234',), {}),
        ('/tmp', '1234', None)),
    ((('postgresql:///foo?dbname=bar',), {}),
        (None, None, 'bar')),
    ((('postgresql://example.com/foo?hostaddr=1.2.3.4&host=bar',), {}),
        ('1.2.3.4', None, 'foo')),
])
def test_uri(connect_params, expected):
    output = instance_info(*connect_params)
    assert output == expected

@pytest.mark.parametrize('connect_params,expected', [
    ((('postgresql://user:password@/?dbname=bar',), {}),
        (None, None, 'bar')),
    ((('postgresql://user:pass@host/?dbname=bar',), {}),
        ('host', None, 'bar')),
    ((('postgresql://user:password@@/?dbname=bar',), {}),
        (None, None, 'bar')),
    ((('postgresql://@',), {}),
        (None, None, None)),
    ((('postgresql://@@localhost',), {}),
        ('localhost', None, None)),
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

    [('otherhost.com', '8888', None), ('otherhost.com', '8888', None)],
    [('otherhost.com', None, None), ('otherhost.com', '5432', None)],
    [('localhost', '8888', None), ('localhost', '8888', None)],
    [('localhost', None, None), ('localhost', '5432', None)],
    [('127.0.0.1', '8888', None), ('127.0.0.1', '8888', None)],
    [('127.0.0.1', None, None), ('127.0.0.1', '5432', None)],
    [('::1', '8888', None), ('::1', '8888', None)],
    [('::1', None, None), ('::1', '5432', None)],

    # Unix Domain Socket

    [(None, None, None), ('localhost', 'default', None)],
    [(None, '5432', None), ('localhost', 'default', None)],
    [(None, '8888', None), ('localhost', 'default', None)],
    [('/tmp', None, None), ('localhost', '/tmp/.s.PGSQL.5432', None)],
    [('/tmp', '5432', None), ('localhost', '/tmp/.s.PGSQL.5432', None)],
    [('/tmp', '8888', None), ('localhost', '/tmp/.s.PGSQL.8888', None)],
]

@pytest.mark.parametrize('host_port,expected', _test_add_defaults)
def test_add_defaults(host_port, expected):
    actual = _add_defaults(*host_port)
    assert actual == expected
