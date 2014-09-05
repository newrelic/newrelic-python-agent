import pymssql

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

# Connection string from .NET agent
# <add name="MSSQLConnection" connectionString="Server=dotnetDB-SQL.pdx.vm. \
# datanerd.us\SQLEXPRESS;Database=NewRelic;User ID=sa;Password=!4maline!; \
# Trusted_Connection=False;Encrypt=False;Connection Timeout=30;" />

server = "dotnetDB-SQL.pdx.vm.datanerd.us\SQLEXPRESS"
user = "sa"
password = "!4maline!"

_test_execute_via_cursor_scoped_metrics = [
        ('Function/pymssql:connect', 1),
        ('Function/pymssql:Connection.__enter__', 1),
        ('Function/pymssql:Connection.__exit__', 1),
        ('Database/database_pymssql/select', 1),
        ('Database/database_pymssql/insert', 1),
        ('Database/database_pymssql/update', 1),
        ('Database/database_pymssql/delete', 1),
        ('Database/other/sql', 5)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 10),
        ('Database/allOther', 10),
        ('Database/select', 1),
        ('Database/database_pymssql/select', 1),
        ('Database/insert', 1),
        ('Database/database_pymssql/insert', 1),
        ('Database/update', 1),
        ('Database/database_pymssql/update', 1),
        ('Database/delete', 1),
        ('Database/database_pymssql/delete', 1),
        ('Database/other', 5),
        ('Database/other/sql', 5)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    with pymssql.connect(server, user, password, "NewRelic") as connection:

        cursor = connection.cursor()

        cursor.execute("""IF OBJECT_ID('database_pymssql', 'U') IS NOT NULL
                        DROP TABLE database_pymssql""")

        cursor.execute("""create table database_pymssql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_pymssql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_pymssql""")

        for row in cursor:
            assert isinstance(row, tuple)

        cursor.execute("""update database_pymssql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_pymssql where a=2""")

        connection.commit()

        connection.rollback()
        connection.commit()

@validate_transaction_metrics('test_database:test_execute_via_cursor_dict',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict():
    with pymssql.connect(server, user, password, "NewRelic") as connection:

        cursor = connection.cursor(as_dict=True)

        cursor.execute("""IF OBJECT_ID('database_pymssql', 'U') IS NOT NULL
                        DROP TABLE database_pymssql""")

        cursor.execute("""create table database_pymssql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_pymssql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_pymssql""")

        for row in cursor:
            assert isinstance(row, dict)

        cursor.execute("""update database_pymssql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_pymssql where a=2""")

        connection.commit()

        connection.rollback()
        connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/pymssql:connect', 1),
        ('Function/pymssql:Connection.__enter__', 1),
        ('Function/pymssql:Connection.__exit__', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Database/all', 1),
        ('Database/allOther', 1)]

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with pymssql.connect(server, user, password, "NewRelic") as connection:

            raise RuntimeError('error')
    except RuntimeError:
        pass
