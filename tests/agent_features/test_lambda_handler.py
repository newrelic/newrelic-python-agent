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

import functools
from copy import deepcopy

import pytest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_event_attributes import (
    validate_transaction_event_attributes,
)
from testing_support.validators.validate_transaction_trace_attributes import (
    validate_transaction_trace_attributes,
)

from newrelic.api import lambda_handler


# NOTE: this fixture will force all tests in this file to assume that a cold
#       start has occurred, *except* when a test has a parameter named
#       "is_cold" and its value is True
@pytest.fixture(autouse=True)
def force_cold_start_status(request):
    try:
        is_cold_start = request.getfixturevalue("is_cold")
        lambda_handler.COLD_START_RECORDED = not is_cold_start
    except Exception:
        lambda_handler.COLD_START_RECORDED = True


@lambda_handler.lambda_handler()
def handler(event, context):
    return {
        "statusCode": "200",
        "body": "{}",
        "headers": {
            "Content-Type": "application/json",
            "Content-Length": 2,
        },
    }


_override_settings = {
    "attributes.include": ["request.parameters.*", "request.headers.*"],
}
_expected_attributes = {
    "agent": [
        "aws.requestId",
        "aws.lambda.arn",
        "request.method",
        "request.uri",
        "response.status",
        "response.headers.contentType",
        "response.headers.contentLength",
    ],
    "user": [],
    "intrinsic": [],
}

_exact_attrs = {
    "agent": {
        "request.parameters.foo": "bar",
        "request.headers.host": "myhost",
    },
    "user": {},
    "intrinsic": {},
}

empty_event = {}
firehose_event = {
    "records": [
        {
            "recordId": "495469866831355442",
            "data": "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0IDEyMy4=",
            "approximateArrivalTimestamp": 1495072949453,
        }
    ],
    "region": "us-west-2",
    "deliveryStreamArn": "arn:aws:kinesis:EXAMPLE",
    "invocationId": "invocationIdExample",
}


class Context(object):
    aws_request_id = "cookies"
    invoked_function_arn = "arn"
    function_name = "cats"
    function_version = "$LATEST"
    memory_limit_in_mb = 128


@pytest.mark.parametrize("is_cold", (False, True))
def test_lambda_transaction_attributes(is_cold, monkeypatch):
    # setup copies of the attribute lists for this test only
    _forgone_params = {}
    _exact = deepcopy(_exact_attrs)
    _expected = deepcopy(_expected_attributes)

    # if we have a cold start, then we should see aws.lambda.coldStart=True
    if is_cold:
        _exact["agent"]["aws.lambda.coldStart"] = True
        _expected["agent"].append("aws.lambda.coldStart")

    # otherwise, then we need to make sure that we don't see it at all
    else:
        _forgone_params = {"agent": ["aws.lambda.coldStart"], "user": [], "intrinsic": []}

    @validate_transaction_trace_attributes(required_params=_expected, forgone_params=_forgone_params)
    @validate_transaction_event_attributes(
        required_params=_expected, forgone_params=_forgone_params, exact_attrs=_exact
    )
    @override_application_settings(_override_settings)
    def _test():
        monkeypatch.setenv("AWS_REGION", "earth")
        handler(
            {
                "httpMethod": "GET",
                "path": "/",
                "headers": {
                    "HOST": "myhost",
                },
                "queryStringParameters": {"foo": "bar"},
                "multiValueQueryStringParameters": {"foo": ["bar"]},
            },
            Context,
        )

    _test()


@validate_transaction_trace_attributes(_expected_attributes)
@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_lambda_malformed_api_gateway_payload(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "earth")
    handler(
        {
            "httpMethod": "GET",
            "path": "/",
            "headers": {},
            "queryStringParameters": 42,
            "multiValueQueryStringParameters": 42,
        },
        Context,
    )


_malformed_request_attributes = {
    "agent": [
        "aws.requestId",
        "aws.lambda.arn",
    ],
    "user": [],
    "intrinsic": [],
}


@validate_transaction_trace_attributes(_malformed_request_attributes)
@validate_transaction_event_attributes(_malformed_request_attributes)
@override_application_settings(_override_settings)
def test_lambda_malformed_request_headers():
    handler(
        {
            "httpMethod": "GET",
            "path": "/",
            "headers": None,
        },
        Context,
    )


_malformed_response_attributes = {
    "agent": [
        "aws.requestId",
        "aws.lambda.arn",
        "request.method",
        "request.uri",
        "response.status",
    ],
    "user": [],
    "intrinsic": [],
}


@validate_transaction_trace_attributes(_malformed_response_attributes)
@validate_transaction_event_attributes(_malformed_response_attributes)
@override_application_settings(_override_settings)
def test_lambda_malformed_response_headers():
    @lambda_handler.lambda_handler()
    def handler(event, context):
        return {
            "statusCode": 200,
            "body": "{}",
            "headers": None,
        }

    handler(
        {
            "httpMethod": "GET",
            "path": "/",
            "headers": {},
        },
        Context,
    )


_no_status_code_response = {
    "agent": [
        "aws.requestId",
        "aws.lambda.arn",
        "request.method",
        "request.uri",
        "response.headers.contentType",
        "response.headers.contentLength",
    ],
    "user": [],
    "intrinsic": [],
}


@validate_transaction_trace_attributes(_no_status_code_response)
@validate_transaction_event_attributes(_no_status_code_response)
@override_application_settings(_override_settings)
def test_lambda_no_status_code_response():
    @lambda_handler.lambda_handler()
    def handler(event, context):
        return {
            "body": "{}",
            "headers": {
                "Content-Type": "application/json",
                "Content-Length": 2,
            },
        }

    handler(
        {
            "httpMethod": "GET",
            "path": "/",
            "headers": {},
        },
        Context,
    )


@pytest.mark.parametrize("event,arn", ((empty_event, None), (firehose_event, "arn:aws:kinesis:EXAMPLE")))
def test_lambda_event_source_arn_attribute(event, arn):
    if arn is None:
        _exact = None
        _expected = None
        _forgone = {
            "user": [],
            "intrinsic": [],
            "agent": ["aws.lambda.eventSource.arn"],
        }
    else:
        _exact = {
            "user": {},
            "intrinsic": {},
            "agent": {"aws.lambda.eventSource.arn": arn},
        }
        _expected = {
            "user": [],
            "intrinsic": [],
            "agent": ["aws.lambda.eventSource.arn"],
        }
        _forgone = None

    @validate_transaction_trace_attributes(required_params=_expected, forgone_params=_forgone)
    @validate_transaction_event_attributes(required_params=_expected, forgone_params=_forgone, exact_attrs=_exact)
    @override_application_settings(_override_settings)
    def _test():
        handler(event, Context)

    _test()


@pytest.mark.parametrize(
    "api",
    (
        lambda_handler.lambda_handler,
        functools.partial(lambda_handler.LambdaHandlerWrapper, handler),
    ),
)
def test_deprecation_warnings(api):
    with pytest.deprecated_call():
        api()
