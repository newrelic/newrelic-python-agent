import pytest

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.core.config import global_settings
from testing_support.fixtures import override_generic_settings

from testing_support.validators.validate_serverless_data import (
        validate_serverless_data)
from testing_support.validators.validate_serverless_payload import (
        validate_serverless_payload)


@pytest.fixture(scope='module')
def serverless_application():
    settings = global_settings()
    orig = settings.serverless_mode
    settings.serverless_mode = True

    application_name = 'Python Agent Test (test_serverless_mode)'
    application = application_instance(application_name)
    application.activate()

    yield application

    settings.serverless_mode = orig


def test_serverless_payload(capsys, serverless_application):

    @override_generic_settings(serverless_application.settings, {
        'distributed_tracing.enabled': True,
    })
    @validate_serverless_data(
            expected_methods=('metric_data', 'analytic_event_data'),
            forgone_methods=('preconnect', 'connect', 'get_agent_commands'))
    @validate_serverless_payload()
    @background_task(
            application=serverless_application,
            name='test_serverless_payload')
    def _test():
        transaction = current_transaction()
        assert transaction.settings.serverless_mode

    _test()

    out, err = capsys.readouterr()

    # Validate that something is printed to stdout
    assert out


def test_no_cat_headers(serverless_application):
    @background_task(
            application=serverless_application,
            name='test_cat_headers')
    def _test_cat_headers():
        transaction = current_transaction()

        payload = ExternalTrace.generate_request_headers(transaction)
        assert not payload

        trace = ExternalTrace(transaction, 'testlib', 'http://example.com')
        response_headers = [('X-NewRelic-App-Data', 'Cookies')]
        with trace:
            trace.process_response_headers(response_headers)

        assert transaction.settings.cross_application_tracer.enabled is False

    _test_cat_headers()


def test_dt_outbound(serverless_application):
    @override_generic_settings(serverless_application.settings, {
        'distributed_tracing.enabled': True,
        'account_id': '1',
        'trusted_account_key': '1',
        'primary_application_id': '1',
    })
    @background_task(
            application=serverless_application,
            name='test_dt_outbound')
    def _test_dt_outbound():
        transaction = current_transaction()
        payload = ExternalTrace.generate_request_headers(transaction)
        assert payload

    _test_dt_outbound()


def test_dt_inbound(serverless_application):
    @override_generic_settings(serverless_application.settings, {
        'distributed_tracing.enabled': True,
        'account_id': '1',
        'trusted_account_key': '1',
        'primary_application_id': '1',
    })
    @background_task(
            application=serverless_application,
            name='test_dt_inbound')
    def _test_dt_inbound():
        transaction = current_transaction()

        payload = {
            'v': [0, 1],
            'd': {
                'ty': 'Mobile',
                'ac': '1',
                'tk': '1',
                'ap': '2827902',
                'pa': '5e5733a911cfbc73',
                'id': '7d3efb1b173fecfa',
                'tr': 'd6b4ba0c3a712ca',
                'ti': 1518469636035,
                'tx': '8703ff3d88eefe9d',
            }
        }

        result = transaction.accept_distributed_trace_payload(payload)
        assert result

    _test_dt_inbound()
