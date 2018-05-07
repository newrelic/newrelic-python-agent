import pytest

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

import cx_Oracle

dsn = cx_Oracle.makedsn(host='localhost', port='1521', service_name='ORCLCDB')


def _execute(connection):
    cursor = connection.cursor()

    try:
        sql = 'drop table datastore_oracle'
        cursor.execute(sql)
    except cx_Oracle.DatabaseError:
        pass

    sql = 'create table datastore_oracle (a integer, b real, c varchar(50))'
    cursor.execute(sql)

    sql = 'insert into datastore_oracle values (:p1, :p2, :p3)'
    params = [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')]
    cursor.executemany(sql, params)

    sql = 'select * from datastore_oracle'
    cursor.execute(sql)

    for row in cursor:
        pass

    connection.commit()

    # cursor.callproc('SYSDATE')

    connection.rollback()


metrics = (
    ('Datastore/operation/Oracle/drop', 1),
    ('Datastore/operation/Oracle/create', 1),
    ('Datastore/statement/Oracle/datastore_oracle/insert', 1),
    ('Datastore/statement/Oracle/datastore_oracle/select', 1),
    ('Datastore/operation/Oracle/commit', 1),
    ('Datastore/operation/Oracle/rollback', 1),
)


@validate_transaction_metrics('test_basic',
        background_task=True, scoped_metrics=metrics, rollup_metrics=metrics)
@background_task(name='test_basic')
def test_basic():
    connection = cx_Oracle.connect(user='SYSTEM', password='password', dsn=dsn)
    _execute(connection)


@validate_transaction_metrics('test_connection_pools',
        background_task=True, scoped_metrics=metrics, rollup_metrics=metrics)
@background_task(name='test_connection_pools')
def test_connection_pools():
    pool = cx_Oracle.SessionPool(
            user='SYSTEM', password='password',
            min=1, max=2, increment=1, dsn=dsn)
    connection = pool.acquire()
    _execute(connection)


@pytest.mark.parametrize('unwrapped', (True, False))
@pytest.mark.parametrize('method', ('drop', 'release'))
@background_task(name='test_connection_pool_methods')
def test_connection_pool_methods(method, unwrapped):
    pool = cx_Oracle.SessionPool(
            user='SYSTEM', password='password',
            min=1, max=2, increment=1, dsn=dsn)

    connection = pool.acquire()

    # This connection object is a proxy but can be passed to certain methods on
    # the pool. These methods should unwrap the proxy prior to calling the
    # oracle library.
    method = getattr(pool, method)

    if unwrapped:
        connection = connection.__wrapped__

    # This should not generate an exception
    method(connection)
