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

import pytest
from testing_support.fixtures import validate_transaction_metrics

from newrelic.api.background_task import background_task

_test_basic_metrics = (
    ("OtherTransaction/all", 1),
    ("OtherTransaction/Function/_target_application:resolve_hello", 1),
    ("Function/_target_application:resolve_hello", 1),
    ("Function/graphql.execution.execute:execute", 1),
)


@pytest.fixture()
def graphql_run():
    try:
        from graphql import graphql_sync as graphql
    except ImportError:
        from graphql import graphql

    return graphql


def example_middleware(next, root, info, **args):
    return_value = next(root, info, **args)
    return return_value


@validate_transaction_metrics(
    "_target_application:resolve_hello",
    rollup_metrics=_test_basic_metrics,
    background_task=True,
)
@background_task()
def test_basic(app, graphql_run):
    response = graphql_run(app, "{ hello }")
    assert "Hello!" in str(response.data)


_test_middleware_metrics = (
    ("OtherTransaction/all", 1),
    ("OtherTransaction/Function/_target_application:resolve_hello", 1),
    ("Function/_target_application:resolve_hello", 1),
    ("Function/test_application:example_middleware", 2),  # 2?????
    ("Function/graphql.execution.execute:execute", 1),
)


@validate_transaction_metrics(
    "_target_application:resolve_hello",
    rollup_metrics=_test_middleware_metrics,
    background_task=True,
)
@background_task()
def test_middleware(app, graphql_run):
    response = graphql_run(app, "{ hello }", middleware=[example_middleware])
    assert "Hello!" in str(response.data)
