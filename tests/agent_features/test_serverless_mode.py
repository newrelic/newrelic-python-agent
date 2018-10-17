import pytest

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.core.config import global_settings
from testing_support.fixtures import override_generic_settings

from testing_support.validators.validate_serverless_data import (
        validate_serverless_data)


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
    @background_task(
            application=serverless_application,
            name='test_serverless_payload')
    def _test():
        pass

    _test()

    out, err = capsys.readouterr()

    # Validate that something is printed to stdout
    assert out
