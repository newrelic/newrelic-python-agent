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

import json
import pytest

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.lambda_handler import lambda_handler
from newrelic.api.transaction import current_transaction
from newrelic.core.config import global_settings

from testing_support.fixtures import override_generic_settings
from testing_support.validators.validate_serverless_data import (
        validate_serverless_data)
from testing_support.validators.validate_serverless_payload import (
        validate_serverless_payload)
from testing_support.validators.validate_serverless_metadata import (
        validate_serverless_metadata)


@pytest.fixture(scope='function')
def serverless_application(request):
    settings = global_settings()
    orig = settings.serverless_mode.enabled
    settings.serverless_mode.enabled = True

    application_name = 'Python Agent Test (test_serverless_mode:%s)' % (
            request.node.name)
    application = application_instance(application_name)
    application.activate()

    yield application

    settings.serverless_mode.enabled = orig


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
        assert transaction.settings.serverless_mode.enabled

    _test()

    out, err = capsys.readouterr()

    # Validate that something is printed to stdout
    assert out

    # Verify that the payload is loadable JSON
    payload = json.loads(out)


def test_no_cat_headers(serverless_application):
    @background_task(
            application=serverless_application,
            name='test_cat_headers')
    def _test_cat_headers():
        transaction = current_transaction()

        payload = ExternalTrace.generate_request_headers(transaction)
        assert not payload

        trace = ExternalTrace('testlib', 'http://example.com')
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


@pytest.mark.parametrize('arn_set', (True, False))
def test_payload_metadata_arn(serverless_application, arn_set):

    # If the session object gathers the arn from the settings object before the
    # lambda handler records it there, then this test will fail.

    settings = global_settings()
    original_metadata = settings.aws_lambda_metadata.copy()

    arn = None
    if arn_set:
        arn = 'arrrrrrrrrrRrrrrrrrn'

    settings.aws_lambda_metadata.update({'arn': arn, 'function_version': '$LATEST'})

    class Context(object):
        invoked_function_arn = arn

    @validate_serverless_metadata(exact_metadata={'arn': arn})
    @lambda_handler(application=serverless_application)
    def handler(event, context):
        assert settings.aws_lambda_metadata['arn'] == arn
        return {}

    try:
        handler({}, Context)
    finally:
        settings.aws_lambda_metadata = original_metadata
