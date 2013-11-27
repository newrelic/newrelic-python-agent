import sqlite3 as database
import os

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DATABASE_DIR = os.environ.get('TOX_ENVDIR', '.')
DATABASE_NAME = os.path.join(DATABASE_DIR, 'database.db')

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
    with database.connect(DATABASE_NAME) as connection:
        cursor = connection.cursor()

        cursor.execute("""drop table if exists database_sqlite""")

        cursor.execute("""create table database_sqlite (a, b, c)""")

        cursor.executemany("""insert into database_sqlite values (?, ?, ?)""",
                [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_sqlite""")

        for row in cursor: pass

        cursor.execute("""update database_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from database_sqlite where a = 2;"""
        cursor.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()

@background_task()
@validate_database_trace_inputs
def test_execute_via_connection():
    with database.connect(DATABASE_NAME) as connection:
        connection.execute("""drop table if exists database_sqlite""")

        connection.execute("""create table database_sqlite (a, b, c)""")

        connection.executemany("""insert into database_sqlite values """
                """(?, ?, ?)""", [(1, 1.0, '1.0'), (2, 2.2, '2.2'),
                (3, 3.3, '3.3')])

        connection.execute("""select * from database_sqlite""")

        connection.execute("""update database_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from database_sqlite where a = 2;"""
        connection.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()
