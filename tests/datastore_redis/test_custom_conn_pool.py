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

"""The purpose of these tests is to confirm that using a non-standard
connection pool that does not have a `connection_kwargs` attribute
will not result in an error.
"""

import pytest
import redis
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = get_package_version_tuple("redis")


class FakeConnectionPool:
    """Connection Pool without connection_kwargs attribute."""

    def __init__(self, connection):
        self.connection = connection

    def get_connection(self, name, *keys, **options):
        return self.connection

    def release(self, connection):
        self.connection.disconnect()

    def disconnect(self):
        self.connection.disconnect()


# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

# We don't record instance metrics when using redis blaster,
# so we just check for base metrics.
datastore_all_metric_count = 5 if REDIS_PY_VERSION >= (5, 0) else 3

_base_scoped_metrics = [
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
]
# client_setinfo was introduced in v5.0.0 and assigns info displayed in client_list output
if REDIS_PY_VERSION >= (5, 0):
    _base_scoped_metrics.append(("Datastore/operation/Redis/client_setinfo", 2))

_base_rollup_metrics = [
    ("Datastore/all", datastore_all_metric_count),
    ("Datastore/allOther", datastore_all_metric_count),
    ("Datastore/Redis/all", datastore_all_metric_count),
    ("Datastore/Redis/allOther", datastore_all_metric_count),
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
]
if REDIS_PY_VERSION >= (5, 0):
    _base_rollup_metrics.append(("Datastore/operation/Redis/client_setinfo", 2))

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Redis/{_host}/{_port}"

instance_metric_count = 5 if REDIS_PY_VERSION >= (5, 0) else 3

_enable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, instance_metric_count))

_disable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, None))

# Operations


def exercise_redis(client):
    client.set("key", "value")
    client.get("key")
    client.execute_command("CLIENT", "LIST", parse="LIST")


# Tests


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 7), reason="Client list command introduced in 2.7")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_custom_conn_pool:test_fake_conn_pool_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_fake_conn_pool_enable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)

    # Get a real connection

    conn = client.connection_pool.get_connection("GET")

    # Replace the original connection pool with one that doesn't
    # have the `connection_kwargs` attribute.

    fake_pool = FakeConnectionPool(conn)
    client.connection_pool = fake_pool
    assert not hasattr(client.connection_pool, "connection_kwargs")

    exercise_redis(client)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 7), reason="Client list command introduced in 2.7")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_custom_conn_pool:test_fake_conn_pool_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_fake_conn_pool_disable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)

    # Get a real connection

    conn = client.connection_pool.get_connection("GET")

    # Replace the original connection pool with one that doesn't
    # have the `connection_kwargs` attribute.

    fake_pool = FakeConnectionPool(conn)
    client.connection_pool = fake_pool
    assert not hasattr(client.connection_pool, "connection_kwargs")

    exercise_redis(client)
