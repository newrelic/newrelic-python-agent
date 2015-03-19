import motor
import pytest

from newrelic.agent import callable_name

# Tests verify that our patch to __getattr__ works.
#
# These are NOT instrumentation tests. Once we add instrumentation,
# these tests can most likely be deleted and replaced with our more
# typical ones that validate metrics.

def test_callable_name_motor_client():
    client = motor.MotorClient()
    assert callable_name(client) == 'motor:MotorClient'

def test_callable_name_motor_database():
    client = motor.MotorClient()
    db = client['database']
    assert callable_name(db) == 'motor:MotorDatabase'

def test_callable_name_motor_collection():
    client = motor.MotorClient()
    db = client['database']
    collection = db['example_collection']
    assert callable_name(collection) == 'motor:MotorCollection'

def test_getattr_dunder_name():
    client = motor.MotorClient()
    with pytest.raises(AttributeError):
        name = client.__name__

def test_underscore_attribute_does_not_raise_error():
    client = motor.MotorClient()
    db = client._db_with_leading_underscore
    assert isinstance(db, motor.MotorDatabase)

def test_underscore_attibute_access():
    client = motor.MotorClient()
    db = client['_db_with_leading_underscore']
    assert isinstance(db, motor.MotorDatabase)
