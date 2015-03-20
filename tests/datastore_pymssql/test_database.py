import pymssql

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import background_task

server = "win-database.pdx.vm.datanerd.us\SQLEXPRESS"
user = "sa"
password = "!4maline!"

# 'DROP' statement is not recognized since our parser isn't designed to handle
# the IF condition which is used by the test. So it is categorized as 'other'.
_test_execute_via_cursor_scoped_metrics = [
        ('Function/pymssql:connect', 1),
        ('Function/pymssql:Connection.__enter__', 1),
        ('Function/pymssql:Connection.__exit__', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/select', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/insert', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/update', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/delete', 1),
        ('Datastore/operation/MSSQL/create', 1),
        ('Datastore/operation/MSSQL/commit', 2),
        ('Datastore/operation/MSSQL/rollback', 1),
        ('Datastore/operation/MSSQL/other', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 10),
        ('Datastore/allOther', 10),
        ('Datastore/MSSQL/all', 10),
        ('Datastore/MSSQL/allOther', 10),
        ('Datastore/operation/MSSQL/select', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/select', 1),
        ('Datastore/operation/MSSQL/insert', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/insert', 1),
        ('Datastore/operation/MSSQL/update', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/update', 1),
        ('Datastore/operation/MSSQL/delete', 1),
        ('Datastore/statement/MSSQL/datastore_pymssql/delete', 1),
        ('Datastore/operation/MSSQL/create', 1),
        ('Datastore/operation/MSSQL/commit', 2),
        ('Datastore/operation/MSSQL/rollback', 1),
        ('Datastore/operation/MSSQL/other', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    with pymssql.connect(server, user, password, "NewRelic") as connection:

        cursor = connection.cursor()

        cursor.execute("""IF OBJECT_ID('datastore_pymssql', 'U') IS NOT NULL
                        DROP TABLE datastore_pymssql""")

        cursor.execute("""create table datastore_pymssql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_pymssql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_pymssql""")

        for row in cursor:
            assert isinstance(row, tuple)

        cursor.execute("""update datastore_pymssql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_pymssql where a=2""")

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

        cursor.execute("""IF OBJECT_ID('datastore_pymssql', 'U') IS NOT NULL
                        DROP TABLE datastore_pymssql""")

        cursor.execute("""create table datastore_pymssql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_pymssql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_pymssql""")

        for row in cursor:
            assert isinstance(row, dict)

        cursor.execute("""update datastore_pymssql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_pymssql where a=2""")

        connection.commit()

        connection.rollback()
        connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/pymssql:connect', 1),
        ('Function/pymssql:Connection.__enter__', 1),
        ('Function/pymssql:Connection.__exit__', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 1),
        ('Datastore/allOther', 1)]

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
