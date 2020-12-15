import pytest

import motor
from motor import MotorClient, MotorDatabase, MotorCollection
try:
    from motor import MotorReplicaSetClient
except ImportError:
    pass

from newrelic.common.object_names import callable_name


# Tests verify that our patch to __getattr__ works.
#
# These are NOT instrumentation tests. Once we add instrumentation,
# these tests can most likely be deleted and replaced with our more
# typical ones that validate metrics.

def test_callable_name_motor_client():
    client = MotorClient()
    assert callable_name(client).endswith(':MotorClient')


@pytest.mark.skipif(motor.version_tuple >= (1, 0),
        reason="Motor 1.0 removed MotorReplicaSetClient")
def test_callable_name_motor_replica_set_client():
    client = MotorReplicaSetClient(replicaSet='foo')
    assert callable_name(client) == 'motor:MotorReplicaSetClient'


def test_callable_name_motor_database():
    client = MotorClient()
    db = client['database']
    assert callable_name(db).endswith(':MotorDatabase')


def test_callable_name_motor_collection():
    client = MotorClient()
    db = client['database']
    collection = db['example_collection']
    assert callable_name(collection).endswith(':MotorCollection')


def test_getattr_dunder_name():
    client = MotorClient()
    with pytest.raises(AttributeError):
        client.__name__


def test_getattr_nr_attribute():
    client = MotorClient()
    with pytest.raises(AttributeError):
        client._nr_object_path


@pytest.mark.skipif(motor.version_tuple >= (0, 6),
        reason="As of Motor 0.6, A database or collection whose name"
        " starts with an underscore can no longer be accessed as a property.")
def test_leading_underscore_attribute_access():
    client = MotorClient()
    db = client._db_with_leading_underscore
    assert isinstance(db, MotorDatabase)


def test_leading_underscore_attribute_getitem():
    client = MotorClient()
    db = client['_db_with_leading_underscore']
    collection = db['_collection_with_leading_underscore']
    assert isinstance(collection, MotorCollection)
