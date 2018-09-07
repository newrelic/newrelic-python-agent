import psycopg2
import psycopg2.extras
import psycopg2.extensions
import pytest

from testing_support.fixtures import (
    validate_transaction_slow_sql_count,
    override_application_settings)
from testing_support.validators.validate_database_node import (
    validate_database_node,
)
from newrelic.core.database_utils import SQLConnections
from testing_support.util import instance_hostname
from utils import DB_SETTINGS, PSYCOPG2_VERSION

from newrelic.api.background_task import background_task


_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']


class CustomConnection(psycopg2.extensions.connection):
    def __init__(self, *args, **kwargs):
        self.ready = False
        return super(CustomConnection, self).__init__(*args, **kwargs)

    def cursor(self, *args, **kwargs):
        assert self.ready  # Force a failure when generating an explain plan
        return super(CustomConnection, self).cursor(*args, **kwargs)


class CustomCursor(psycopg2.extensions.cursor):
    def __init__(self, *args, **kwargs):
        self.ready = False
        return super(CustomCursor, self).__init__(*args, **kwargs)

    def execute(self, *args, **kwargs):
        assert self.ready  # Force a failure when generating an explain plan
        return super(CustomCursor, self).execute(*args, **kwargs)


def _exercise_db(connection_factory=None, cursor_factory=None,
        cursor_kwargs=None):
    cursor_kwargs = cursor_kwargs or {}

    connect_kwargs = {}
    if PSYCOPG2_VERSION >= (2, 5):
        connect_kwargs['cursor_factory'] = cursor_factory

    if connection_factory:
        connect_kwargs['connection_factory'] = connection_factory

    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], **connect_kwargs)
    if hasattr(connection, 'ready'):
        connection.ready = True

    try:
        cursor = connection.cursor(**cursor_kwargs)
        if hasattr(cursor, 'ready'):
            cursor.ready = True

        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))
    finally:
        connection.close()


# Tests


def explain_plan_is_none(node):
    with SQLConnections() as connections:
        explain_plan = node.explain_plan(connections)

    assert explain_plan is None


def explain_plan_is_not_none(node):
    with SQLConnections() as connections:
        explain_plan = node.explain_plan(connections)

    assert explain_plan is not None


# psycopg2 2.5 introduced the scrollable argument
if PSYCOPG2_VERSION < (2, 5):
    SCROLLABLE = (False, )
else:
    SCROLLABLE = (True, False)

# psycopg2 2.4.3 introduced the withold argument
if PSYCOPG2_VERSION < (2, 4, 3):
    WITHHOLD = (False, )
else:
    WITHHOLD = (True, False)


@override_application_settings({
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.record_sql': 'raw',
})
@validate_database_node(explain_plan_is_not_none)
@validate_transaction_slow_sql_count(1)
@background_task(name='test_explain_plan_named_cursors')
@pytest.mark.parametrize('withhold', WITHHOLD)
@pytest.mark.parametrize('scrollable', SCROLLABLE)
def test_explain_plan_named_cursors(withhold, scrollable):
    cursor_kwargs = {
        'name': 'test_explain_plan_named_cursors',
    }

    if withhold:
        cursor_kwargs['withhold'] = withhold

    if scrollable:
        cursor_kwargs['scrollable'] = scrollable

    _exercise_db(cursor_kwargs=cursor_kwargs)


# The following tests will verify that arguments are preserved for an explain
# plan by forcing a failure to be generated when explain plans are created and
# arguments are preserved
@override_application_settings({
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.record_sql': 'raw',
})
@validate_database_node(explain_plan_is_none)
@validate_transaction_slow_sql_count(1)
@background_task(name='test_explain_plan_on_custom_connect_class')
def test_explain_plan_on_custom_connect_class():
    _exercise_db(connection_factory=CustomConnection)


@override_application_settings({
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.record_sql': 'raw',
})
@validate_database_node(explain_plan_is_none)
@validate_transaction_slow_sql_count(1)
@background_task(name='test_explain_plan_on_custom_connect_class')
@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 5),
        reason='psycopg2 2.5 introduced the cursor_factory argument')
def test_explain_plan_on_custom_cursor_class_1():
    _exercise_db(cursor_factory=CustomCursor)


@override_application_settings({
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.record_sql': 'raw',
})
@validate_database_node(explain_plan_is_none)
@validate_transaction_slow_sql_count(1)
@background_task(name='test_explain_plan_on_custom_connect_class')
def test_explain_plan_on_custom_cursor_class_2():
    _exercise_db(cursor_kwargs={'cursor_factory': CustomCursor})
