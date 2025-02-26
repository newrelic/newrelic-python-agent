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

import os

import pytest
from cassandra.cqlengine import columns, connection
from cassandra.cqlengine.management import create_keyspace_simple, drop_keyspace, drop_table, sync_table
from cassandra.cqlengine.models import Model
from cassandra.cqlengine.query import BatchQuery
from testing_support.db_settings import cassandra_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = cassandra_settings()[0]
HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]
KEYSPACE = f"{DB_SETTINGS['keyspace']}_orm"
TABLE_NAME = f"{DB_SETTINGS['table_name']}_orm"
FULL_TABLE_NAME = f"{KEYSPACE}.{TABLE_NAME}"  # Fully qualified table name with keyspace


class ABCModel(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = TABLE_NAME

    a = columns.Integer(primary_key=True)
    b = columns.Double()


@pytest.fixture(scope="function")
def exercise(cluster_options):
    # Silence warning from cqlengine when creating tables
    os.environ["CQLENG_ALLOW_SCHEMA_MANAGEMENT"] = "true"

    def _exercise():
        host = cluster_options.pop("contact_points")
        connection.setup(host, KEYSPACE, **cluster_options)

        # Initial setup
        create_keyspace_simple(KEYSPACE, replication_factor=1)

        # Create initial model
        class ABModel(Model):
            __keyspace__ = KEYSPACE
            __table_name__ = TABLE_NAME

            a = columns.Integer(primary_key=True)
            b = columns.Double()

        drop_table(ABModel)  # Drop initial table if exists
        sync_table(ABModel)  # Create table

        # Alter model via inheritance
        class ABCModel(ABModel):
            c = columns.Text(index=True)

        sync_table(ABCModel)  # Alter table to add colummn

        m1 = ABCModel.create(a=1, b=1.0, c="1.0")  # Insert query

        # Batch insert query
        with BatchQuery() as b:
            ABCModel.batch(b).create(a=2, b=2.0, c="2.0")
            ABCModel.batch(b).create(a=3, b=3.0, c="3.0")

        cursor = ABCModel.objects()  # Select query
        _ = [row for row in cursor]

        # Update query
        m1.update(**{"b": 4.0, "c": "4.0"})
        m1.save()

        ABCModel.filter(a=2).delete()  # Delete query

        drop_table(ABCModel)
        drop_keyspace(KEYSPACE)

    return _exercise


_test_execute_scoped_metrics = [
    ("Function/cassandra.cluster:Cluster.connect", 1),
    ("Datastore/operation/Cassandra/alter", 1),
    ("Datastore/operation/Cassandra/begin", 1),
    ("Datastore/operation/Cassandra/create", 3),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/delete", 1),
    ("Datastore/operation/Cassandra/drop", 2),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/insert", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/select", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/update", 1),
]

_test_execute_rollup_metrics = [
    ("Function/cassandra.cluster:Cluster.connect", 1),
    (f"Datastore/instance/Cassandra/{HOST}/{PORT}", 11),
    ("Datastore/all", 12),
    ("Datastore/allOther", 12),
    ("Datastore/Cassandra/all", 12),
    ("Datastore/Cassandra/allOther", 12),
    ("Datastore/operation/Cassandra/alter", 1),
    ("Datastore/operation/Cassandra/begin", 1),
    ("Datastore/operation/Cassandra/create", 3),
    ("Datastore/operation/Cassandra/delete", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/delete", 1),
    ("Datastore/operation/Cassandra/drop", 2),
    ("Datastore/operation/Cassandra/insert", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/insert", 1),
    ("Datastore/operation/Cassandra/select", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/select", 1),
    ("Datastore/operation/Cassandra/update", 1),
    (f"Datastore/statement/Cassandra/{FULL_TABLE_NAME}/update", 1),
]


@validate_transaction_metrics(
    "test_cqlengine:test_model",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
@background_task()
def test_model(exercise):
    exercise()
