import pymysql

import pwd
import os

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

USER = pwd.getpwuid(os.getuid()).pw_name

DATABASE_NAME = os.environ.get('TDDIUM_DB_MYSQL_NAME', USER)
DATABASE_USER = os.environ.get('TDDIUM_DB_MYSQL_USER', USER)
DATABASE_PASSWORD = os.environ.get('TDDIUM_DB_MYSQL_PASSWORD', '')
DATABASE_HOST = os.environ.get('TDDIUM_DB_MYSQL_HOST', 'localhost')
DATABASE_PORT = int(os.environ.get('TDDIUM_DB_MYSQL_PORT', '3306'))

@transient_function_wrapper('newrelic.api.database_trace',
        'DatabaseTrace.__init__')
def validate_database_trace_inputs(wrapped, instance, args, kwargs):
    def _bind_params(transaction, sql, dbapi2_module=None,
            connect_params=None, cursor_params=None, execute_params=None):
        return (transaction, sql, dbapi2_module, connect_params,
                cursor_params, execute_params)

    (transaction, sql, dbapi2_module, connect_params,
            cursor_params, execute_params) = _bind_params(*args, **kwargs)

    assert hasattr(dbapi2_module, 'connect')

    assert connect_params is None or isinstance(connect_params, tuple)

    if connect_params is not None:
        assert len(connect_params) == 2
        assert isinstance(connect_params[0], tuple)
        assert isinstance(connect_params[1], dict)

    assert cursor_params is None or isinstance(cursor_params, tuple)

    if cursor_params is not None:
        assert len(cursor_params) == 2
        assert isinstance(cursor_params[0], tuple)
        assert isinstance(cursor_params[1], dict)

    assert execute_params is None or isinstance(execute_params, tuple)

    return wrapped(*args, **kwargs)

@background_task()
@validate_database_trace_inputs
def test_execute_via_cursor():
    connection = pymysql.connect(db=DATABASE_NAME, user=DATABASE_USER,
            passwd=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
    
    with connection as cursor:
        cursor.execute("""drop table if exists database_pymysql""")

        cursor.execute("""create table database_pymysql """
               """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_pymysql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_pymysql""")

        for row in cursor: pass

        cursor.execute("""update database_pymysql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_pymysql where a=2""")

    connection.rollback()
    connection.commit()
