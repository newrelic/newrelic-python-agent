import pytest
from newrelic.hooks.database_psycopg2 import instance_info

def test_kwargs():
    args_kwargs = ((), {'database': 'foo', 'host': '1.2.3.4', 'port': 1234})
    output = instance_info(*args_kwargs)
    assert output == ('1.2.3.4', '1234')

def test_arg_str():
    args_kwargs = (("host=foobar port=9876",), {})
    output = instance_info(*args_kwargs)
    assert output == ('foobar', '9876')

def test_missing_port():
    args_kwargs = (("host=foobar",), {})
    output = instance_info(*args_kwargs)
    assert output == ('foobar', None)

def test_missing_host():
    args_kwargs = (("port=5555",), {})
    output = instance_info(*args_kwargs)
    assert output == (None, '5555')

def test_str_in_port():
    args_kwargs = (("port=foobar",), {})
    output = instance_info(*args_kwargs)
    assert output == (None, 'foobar')
