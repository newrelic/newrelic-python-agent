import pytest
from testing_support.fixtures import (override_application_settings,
        validate_transaction_trace_attributes,
        validate_transaction_event_attributes)
import newrelic.api.lambda_handler as lambda_handler


@pytest.fixture(autouse=True)
def force_cold_start():
    lambda_handler.COLD_START_TIME = None


@lambda_handler.lambda_handler()
def handler(event, context):
    return {
        'statusCode': '200',
        'body': '{}',
        'headers': {
            'Content-Type': 'application/json',
            'Content-Length': 2,
        },
    }


_override_settings = {
    'attributes.include': ['aws.*', 'memoryLimit', 'coldStartTime',
            'request.parameters.*'],
}
_expected_attributes = {
    'agent': [
        'aws.requestId',
        'aws.arn',
        'aws.region',
        'aws.functionName',
        'aws.functionVersion',
        'memoryLimit',
        'coldStartTime',
        'response.status',
        'response.headers.contentType',
        'response.headers.contentLength',
    ],
    'user': [],
    'intrinsic': [],
}

_exact_attrs = {
    'agent': {
        'memoryLimit': 128 * 2**20,
        'request.parameters.foo': 'bar',
    },
    'user': {},
    'intrinsic': {}
}


class Context(object):
    aws_request_id = 'cookies'
    invoked_function_arn = 'arn'
    function_name = 'cats'
    function_version = '$LATEST'
    memory_limit_in_mb = 128


@validate_transaction_trace_attributes(_expected_attributes)
@validate_transaction_event_attributes(
    _expected_attributes, exact_attrs=_exact_attrs)
@override_application_settings(_override_settings)
def test_lambda_transaction_attributes(monkeypatch):
    monkeypatch.setenv('AWS_REGION', 'earth')
    handler({
        'httpMethod': 'GET',
        'path': '/',
        'headers': {},
        'queryStringParameters': {'foo': 'bar'},
        'multiValueQueryStringParameters': {'foo': ['bar']},
    }, Context)


@validate_transaction_trace_attributes(_expected_attributes)
@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_lambda_malformed_api_gateway_payload(monkeypatch):
    monkeypatch.setenv('AWS_REGION', 'earth')
    handler({
        'httpMethod': 'GET',
        'path': '/',
        'headers': {},
        'queryStringParameters': 42,
        'multiValueQueryStringParameters': 42,
    }, Context)
