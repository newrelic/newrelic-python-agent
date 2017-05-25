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

def _exercise_db(connection):
    with connection as cursor:
        cursor.execute("""drop table if exists datastore_mysqldb""")

        cursor.execute("""create table datastore_mysqldb """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_mysqldb """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_mysqldb""")

        for row in cursor: pass

        cursor.execute("""update datastore_mysqldb set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_mysqldb where a=2""")

        cursor.execute("""show authors""")

    connection.commit()
    connection.rollback()
    connection.commit()

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics('test_alias:test_connect_using_alias_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_connect_using_alias_enable():
    connection = MySQLdb.Connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])
    _exercise_db(connection)

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics('test_alias:test_connect_using_alias_disable',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_connect_using_alias_disable():
    connection = MySQLdb.Connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])
    _exercise_db(connection)
