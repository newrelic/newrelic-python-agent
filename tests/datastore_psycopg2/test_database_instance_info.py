import pytest
from newrelic.hooks.database_psycopg2 import instance_info, _add_defaults

def test_kwargs():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': 1234})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', '1234')

def test_arg_str():
    connect_params = (("host=foobar port=9876",), {})
    output = instance_info(*connect_params)
    assert output == ('foobar', '9876')

def test_kwargs_str_for_port():
    connect_params = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': '1234'})
    output = instance_info(*connect_params)
    assert output == ('1.2.3.4', '1234')

def test_arg_str_missing_port():
    connect_params = (("host=foobar",), {})
    output = instance_info(*connect_params)
    assert output == ('foobar', None)

def test_arg_str_multiple_host():
    connect_params = (("host=foobar host=barbaz",), {})
    output = instance_info(*connect_params)
    assert output == ('barbaz', None)

def test_arg_str_multiple_port():
    connect_params = (("port=5555 port=7777",), {})
    output = instance_info(*connect_params)
    assert output == (None, '7777')

def test_arg_str_missing_host():
    connect_params = (("port=5555",), {})
    output = instance_info(*connect_params)
    assert output == (None, '5555')

def test_arg_str_missing_host_and_port():
    connect_params = (("nothing=here",), {})
    output = instance_info(*connect_params)
    assert output == (None, None)

def test_malformed_arg_str():
    connect_params = (("this_is_malformed",), {})
    output = instance_info(*connect_params)
    assert output == ('unknown', 'unknown')

def test_str_in_port_arg_str():
    connect_params = (("port=foobar",), {})
    output = instance_info(*connect_params)
    assert output == (None, 'foobar')

@pytest.mark.parametrize('connect_params,expected', [
    ((('postgresql://',), {}),
        (None, None)),
    ((('postgresql://localhost',), {}),
        ('localhost', None)),
    ((('postgresql://localhost:5433',), {}),
        ('localhost', '5433')),
    ((('postgresql://localhost/mydb',), {}),
        ('localhost', None)),
    ((('postgresql://user@localhost',), {}),
        ('localhost', None)),
    ((('postgresql://user:secret@localhost',), {}),
        ('localhost', None)),
    ((('postgresql://[2001:db8::1234]/database',), {}),
        ('[2001:db8::1234]', None)),
    ((('postgresql://[2001:db8::1234]:2222/database',), {}),
        ('[2001:db8::1234]', '2222')),
    ((('postgresql:///dbname?host=/var/lib/postgresql',), {}),
        ('/var/lib/postgresql',  None)),
    ((('postgresql://%2Fvar%2Flib%2Fpostgresql/dbname',), {}),
        ('/var/lib/postgresql',  None)),
    ((('postgresql://other@localhost/otherdb?c=10&a=myapp',), {}),
        ('localhost', None)),
    ((('postgresql:///',), {}),
        (None, None)),
    ((('postgresql:///dbname?host=foo',), {}),
        ('foo', None)),
    ((('postgresql:///dbname?port=1234',), {}),
        (None, '1234')),
    ((('postgresql:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234')),
    ((('postgres:///dbname?host=foo&port=1234',), {}),
        ('foo', '1234')),
    ((('postgres://localhost:5444/blah?host=::1',), {}),
        ('::1', '5444')),
    ((('postgresql:///dbname?host=foo&port=1234&host=bar',), {}),
        ('bar', '1234')),
    ((('postgresql://%2Ftmp:1234',), {}),
        ('/tmp', '1234')),
])
def test_uri(connect_params, expected):
    output = instance_info(*connect_params)
    assert output == expected

def test_bad_uri():
    connect_params = (("blah:///foo",), {})
    output = instance_info(*connect_params)
    assert output == ('unknown', 'unknown')

_test_add_defaults = [

    # TCP/IP

    [('otherhost.com', '8888'), ('otherhost.com', '8888')],
    [('otherhost.com', None), ('otherhost.com', '5432')],
    [('localhost', '8888'), ('localhost', '8888')],
    [('localhost', None), ('localhost', '5432')],
    [('127.0.0.1', '8888'), ('127.0.0.1', '8888')],
    [('127.0.0.1', None), ('127.0.0.1', '5432')],
    [('::1', '8888'), ('::1', '8888')],
    [('::1', None), ('::1', '5432')],

    # Unix Domain Socket

    [(None, None), ('localhost', 'default')],
    [(None, '5432'), ('localhost', 'default')],
    [(None, '8888'), ('localhost', 'default')],
    [('/tmp', None), ('localhost', '/tmp/.s.PGSQL.5432')],
    [('/tmp', '5432'), ('localhost', '/tmp/.s.PGSQL.5432')],
    [('/tmp', '8888'), ('localhost', '/tmp/.s.PGSQL.8888')],
]

@pytest.mark.parametrize('host_port,expected', _test_add_defaults)
def test_add_defaults(host_port, expected):
    actual = _add_defaults(*host_port)
    assert actual == expected
