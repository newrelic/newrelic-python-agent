import pytest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.datastore_trace import DatastoreTrace
from testing_support.fixtures import override_application_settings


@pytest.mark.parametrize('instance_reporting', (False, True))
@pytest.mark.parametrize('db_name_reporting', (False, True))
def test_datastore_trace_settings(db_name_reporting, instance_reporting):
    def _check_datastore_trace_values(trace,
            host, port_path_or_id, database_name):

        if instance_reporting:
            assert trace.host == host
            assert trace.port_path_or_id == port_path_or_id
        else:
            assert trace.host is None
            assert trace.port_path_or_id is None

        if db_name_reporting:
            assert trace.database_name == database_name
        else:
            assert trace.database_name is None

    @override_application_settings({
        'datastore_tracer.database_name_reporting.enabled': db_name_reporting,
        'datastore_tracer.instance_reporting.enabled': instance_reporting
    })
    @background_task()
    def _test_datastore_trace_settings():
        transaction = current_transaction()

        with DatastoreTrace(transaction, product='Redis', target='target',
                operation='operation', host='same1', port_path_or_id='same2',
                database_name='same3') as trace:

            _check_datastore_trace_values(trace, 'same1', 'same2', 'same3')

            trace.host = 'diff1'
            trace.port_path_or_id = 'diff2'
            trace.database_name = 'diff3'

            _check_datastore_trace_values(trace, 'diff1', 'diff2', 'diff3')

    _test_datastore_trace_settings()
