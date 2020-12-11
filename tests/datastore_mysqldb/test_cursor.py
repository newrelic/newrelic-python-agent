import MySQLdb

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, override_application_settings)
from testing_support.settings import mysql_multiple_settings
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = mysql_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Function/MySQLdb:Connect', 1),
        ('Function/MySQLdb.connections:Connection.__enter__', 1),
        ('Function/MySQLdb.connections:Connection.__exit__', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/MySQL/all', 12),
        ('Datastore/MySQL/allOther', 12),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/MySQL/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 11)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

# Query

def _exercise_db(connection, table_name):
    with connection as cursor:
        cursor.execute("""drop table if exists %s""" % table_name)

        cursor.execute("""create table %s """
                """(a integer, b real, c text)""" % table_name)

        cursor.executemany("""insert into %s """
                """values (%s, %s, %s)""", [(table_name, 1, 1.0, '1.0'),
                (table_name, 2, 2.2, '2.2'), (table_name, 3, 3.3, '3.3')])

        cursor.execute("""select * from %s""" % table_name)

        for row in cursor: pass

        cursor.execute("""update %s set a=%s, b=%s, """
                """c=%s where a=%s""", (table_name, 4, 4.0, '4.0', 1))

        cursor.execute("""delete from %s where a=2""" % table_name)

        cursor.execute("""show authors""")

    connection.commit()
    connection.rollback()
    connection.commit()

# Tests

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics('test_cursor:test_execute_via_cursor_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_execute_via_cursor_enable(table_name):
    connection = MySQLdb.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])
    _exercise_db(connection, table_name)

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics('test_cursor:test_execute_via_cursor_disable',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_execute_via_cursor_disable(table_name):
    connection = MySQLdb.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])
    _exercise_db(connection, table_name)
