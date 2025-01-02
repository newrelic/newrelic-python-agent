# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from testing_support.db_settings import cassandra_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import (
    validate_database_trace_inputs,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

DB_SETTINGS = cassandra_settings()[0]
TABLE_NAME = DB_SETTINGS["table_name"]
KEYSPACE = DB_SETTINGS["keyspace"]


def exercise(session):
    session.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {KEYSPACE} WITH REPLICATION = {{ 'class' : 'SimpleStrategy', 'replication_factor' : 1 }};"
    )
    session.set_keyspace(KEYSPACE)

    session.execute(f"""drop table if exists {TABLE_NAME}""")
    session.execute(f"""create table {TABLE_NAME} (a int, b double, c ascii, primary key (a))""")

    row_data = [{"a": 1, "b": 1.0, "c": "1.0"}, {"a": 2, "b": 2.2, "c": "2.2"}, {"a": 3, "b": 3.3, "c": "3.3"}]
    for row in row_data:
        session.execute(f"insert into {TABLE_NAME} (a, b, c) values (%(a)s, %(b)s, %(c)s)", row)

    cursor = session.execute(f"""select * from {TABLE_NAME}""")

    _ = [row for row in cursor]

    session.execute(
        f"update {TABLE_NAME} set b=%(b)s, c=%(c)s where a=%(a)s",
        {"a": 1, "b": 4.0, "c": "4.0"},
    )

    session.execute(f"""delete from {TABLE_NAME} where a=2""")

    # session.execute("commit")
    # session.execute("rollback")
    # session.execute("commit")


_test_execute_scoped_metrics = [
    # ("Function/cassandra_driver:connect", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/select", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/insert", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/update", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/delete", 1),
    # ("Datastore/statement/Cassandra/now/call", 1),
    # ("Datastore/statement/Cassandra/pg_sleep/call", 1),
    # ("Datastore/operation/Cassandra/drop", 1),
    # ("Datastore/operation/Cassandra/create", 1),
    ("Datastore/operation/Cassandra/commit", 3),
    # ("Datastore/operation/Cassandra/rollback", 1),
    # ("Datastore/operation/Cassandra/other", 1),
]

_test_execute_rollup_metrics = [
    ("Datastore/all", 14),
    # ("Datastore/allOther", 14),
    # ("Datastore/Cassandra/all", 14),
    # ("Datastore/Cassandra/allOther", 14),
    # ("Datastore/operation/Cassandra/select", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/select", 1),
    # ("Datastore/operation/Cassandra/insert", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/insert", 1),
    # ("Datastore/operation/Cassandra/update", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/update", 1),
    # ("Datastore/operation/Cassandra/delete", 1),
    # (f"Datastore/statement/Cassandra/{TABLE_NAME}/delete", 1),
    # ("Datastore/operation/Cassandra/drop", 1),
    # ("Datastore/operation/Cassandra/create", 1),
    # ("Datastore/statement/Cassandra/now/call", 1),
    # ("Datastore/statement/Cassandra/pg_sleep/call", 1),
    # ("Datastore/operation/Cassandra/call", 2),
    # ("Datastore/operation/Cassandra/commit", 3),
    # ("Datastore/operation/Cassandra/rollback", 1),
    # ("Datastore/operation/Cassandra/other", 1),
    # (f"Datastore/instance/Cassandra/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 13),
    # ("Function/cassandra_driver.driver.dbapi20:connect", 1),
    # ("Function/cassandra_driver.driver.dbapi20:Session.__enter__", 1),
    # ("Function/cassandra_driver.driver.dbapi20:Session.__exit__", 1),
]


@validate_transaction_metrics(
    "test_database:test_execute",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
# @validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute(cluster):
    with cluster.connect() as session:
        exercise(session)


# _test_rollback_on_exception_scoped_metrics = [
#     ("Function/cassandra_driver.driver.dbapi20:connect", 1),
#     ("Function/cassandra_driver.driver.dbapi20:Session.__enter__", 1),
#     ("Function/cassandra_driver.driver.dbapi20:Session.__exit__", 1),
#     ("Datastore/operation/Cassandra/rollback", 1),
# ]

# _test_rollback_on_exception_rollup_metrics = [
#     ("Datastore/all", 2),
#     ("Datastore/allOther", 2),
#     ("Datastore/Cassandra/all", 2),
#     ("Datastore/Cassandra/allOther", 2),
# ]


# @validate_transaction_metrics(
#     "test_database:test_rollback_on_exception",
#     scoped_metrics=_test_rollback_on_exception_scoped_metrics,
#     rollup_metrics=_test_rollback_on_exception_rollup_metrics,
#     background_task=True,
# )
# @validate_database_trace_inputs(sql_parameters_type=tuple)
# @background_task()
# def test_rollback_on_exception(cluster):
#     try:
#         with cluster.connect() as session:
#             raise RuntimeError("error")

#     except RuntimeError:
#         pass
