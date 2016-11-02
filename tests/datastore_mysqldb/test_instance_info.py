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
