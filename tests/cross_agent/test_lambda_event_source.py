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
import os
import pytest

from newrelic.api.lambda_handler import lambda_handler
from testing_support.fixtures import (override_application_settings,
        validate_transaction_event_attributes)

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures'))
FIXTURE = os.path.join(FIXTURE_DIR, 'lambda_event_source.json')
tests = {}
events = {}


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        for test in json.loads(fh.read()):
            test_name = test.pop('name')

            test_file = test_name + '.json'
            path = os.path.join(FIXTURE_DIR, 'lambda_event_source', test_file)
            with open(path, 'r') as fh:
                events[test_name] = json.loads(fh.read())

            tests[test_name] = test
    return tests.keys()


class Context(object):
    aws_request_id = 'cookies'
    invoked_function_arn = 'arn'
    function_name = 'cats'
    function_version = '$LATEST'
    memory_limit_in_mb = 128


@lambda_handler()
def handler(event, context):
    return {
        'statusCode': '200',
        'body': '{}',
        'headers': {
            'Content-Type': 'application/json',
            'Content-Length': 2,
        },
    }


@pytest.mark.parametrize('test_name', _load_tests())
def test_lambda_event_source(test_name):
    _exact = {'user': {}, 'intrinsic': {}, 'agent': {}}

    expected_arn = tests[test_name].get('aws.lambda.eventSource.arn', None)
    if expected_arn:
        _exact['agent']['aws.lambda.eventSource.arn'] = expected_arn
    else:
        pytest.skip("Nothing to test!")
        return

    @override_application_settings({'attributes.include': ['aws.*']})
    @validate_transaction_event_attributes({}, exact_attrs=_exact)
    def _test():
        handler(events[test_name], Context)

    _test()
