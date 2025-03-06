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

import pytest
from cassandra.query import SimpleStatement
from testing_support.db_settings import cassandra_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = cassandra_settings()[0]
HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]
KEYSPACE = DB_SETTINGS["keyspace"]
TABLE_NAME = DB_SETTINGS["table_name"]
FULL_TABLE_NAME = f"{KEYSPACE}.{TABLE_NAME}"  # Fully qualified table name with keyspace
REPLICATION_STRATEGY = "{ 'class' : 'SimpleStrategy', 'replication_factor' : 1 }"


@pytest.fixture(scope="function")
def exercise(cluster):
    def _exercise(is_async=False):
        with cluster.connect() as session:
            # Run async queries with execute_async() and .result(), and sync queries with execute()
            if is_async:
                execute_query = lambda query, *args: session.execute_async(query, *args).result()
            else:
                execute_query = lambda query, *args: session.execute(query, *args)

            execute_query(
                f"create keyspace if not exists {KEYSPACE} with replication = {REPLICATION_STRATEGY} and durable_writes = false;"
            )
            session.set_keyspace(KEYSPACE)  # Should be captured as "USE" query

            # Alter keyspace to enable durable writes
            execute_query(
                f"alter keyspace {KEYSPACE} with replication = {REPLICATION_STRATEGY} and durable_writes = true;"
            )

            execute_query(f"drop table if exists {FULL_TABLE_NAME}")
            execute_query(f"create table {FULL_TABLE_NAME} (a int, b double, primary key (a))")
            execute_query(f"alter table {FULL_TABLE_NAME} add c ascii")

            execute_query(f"create index {TABLE_NAME}_index on {FULL_TABLE_NAME} (c)")

            execute_query(
                f"insert into {FULL_TABLE_NAME} (a, b, c) values (%(a)s, %(b)s, %(c)s)", {"a": 1, "b": 1.0, "c": "1.0"}
            )

            execute_query(
                f"""
                begin batch
                insert into {FULL_TABLE_NAME} (a, b, c) values (%(a1)s, %(b1)s, %(c1)s);
                insert into {FULL_TABLE_NAME} (a, b, c) values (%(a2)s, %(b2)s, %(c2)s);
                apply batch;
                """,
                {"a1": 2, "b1": 2.2, "c1": "2.2", "a2": 3, "b2": 3.3, "c2": "3.3"},
            )

            cursor = execute_query(f"select * from {FULL_TABLE_NAME}")
            _ = [row for row in cursor]

            execute_query(
                f"update {FULL_TABLE_NAME} set b=%(b)s, c=%(c)s where a=%(a)s", {"a": 1, "b": 4.0, "c": "4.0"}
            )
            execute_query(f"delete from {FULL_TABLE_NAME} where a=2")
            execute_query(f"truncate {FULL_TABLE_NAME}")

            # SimpleStatement
            simple_statement = SimpleStatement(f"insert into {FULL_TABLE_NAME} (a, b, c) values (%s, %s, %s)")
            execute_query(simple_statement, (6, 6.0, "6.0"))

            # PreparedStatement
            prepared_statement = session.prepare(f"insert into {FULL_TABLE_NAME} (a, b, c) values (?, ?, ?)")
            execute_query(prepared_statement, (5, 5.0, "5.0"))

            # BoundStatement
            bound_statement = prepared_statement.bind((7, 7.0, "7.0"))
            execute_query(bound_statement, {"a": 5, "b": 5.0, "c": "5.0"})

            execute_query(f"drop index {TABLE_NAME}_index")
            execute_query(f"drop table {FULL_TABLE_NAME}")
            execute_query(f"drop keyspace {KEYSPACE}")

    return _exercise


_test_execute_scoped_metrics = [
    ("Function/cassandra.cluster:Cluster.connect", 1),
    ("Datastore/operation/Cassandra/alter", 2),
    ("Datastore/operation/Cassandra/begin", 1),
    ("Datastore/operation/Cassandra/create", 3),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/delete", 1),
    ("Datastore/operation/Cassandra/drop", 4),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/insert", 4),
    ("Datastore/operation/Cassandra/other", 2),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/select", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/update", 1),
]

_test_execute_rollup_metrics = [
    ("Function/cassandra.cluster:Cluster.connect", 1),
    (f"Datastore/instance/Cassandra/{HOST}/{PORT}", 19),
    ("Datastore/all", 20),
    ("Datastore/allOther", 20),
    ("Datastore/Cassandra/all", 20),
    ("Datastore/Cassandra/allOther", 20),
    ("Datastore/operation/Cassandra/alter", 2),
    ("Datastore/operation/Cassandra/begin", 1),
    ("Datastore/operation/Cassandra/create", 3),
    ("Datastore/operation/Cassandra/delete", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/delete", 1),
    ("Datastore/operation/Cassandra/drop", 4),
    ("Datastore/operation/Cassandra/insert", 4),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/insert", 4),
    ("Datastore/operation/Cassandra/other", 2),
    ("Datastore/operation/Cassandra/select", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/select", 1),
    ("Datastore/operation/Cassandra/update", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/update", 1),
]


@validate_transaction_metrics(
    "test_cassandra:test_execute",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
@background_task()
def test_execute(exercise):
    exercise(is_async=False)


@validate_transaction_metrics(
    "test_cassandra:test_execute_async",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
@background_task()
def test_execute_async(exercise):
    exercise(is_async=True)
