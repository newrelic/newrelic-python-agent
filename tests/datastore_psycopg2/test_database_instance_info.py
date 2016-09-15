import pytest
from newrelic.hooks.database_psycopg2 import instance_info

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

