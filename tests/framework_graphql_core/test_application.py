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
from testing_support.fixtures import validate_transaction_metrics, validate_transaction_errors

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

@pytest.fixture(scope="session")
def is_graphql_2():
    from graphql import __version__ as version
    major_version = int(version.split(".")[0])
    return major_version == 2

@pytest.fixture(scope="session")
def graphql_run():
    try:
        from graphql import graphql_sync as graphql
    except ImportError:
        from graphql import graphql

    return graphql


def example_middleware(next, root, info, **args):
    return_value = next(root, info, **args)
    return return_value

def error_middleware(next, root, info, **args):
    raise RuntimeError("Runtime Error!")

_runtime_error_name = callable_name(RuntimeError)
_test_runtime_error = [(_runtime_error_name, "Runtime Error!")]


def test_basic(app, graphql_run, is_graphql_2):
    _test_basic_metrics = [
        ("OtherTransaction/all", 1),
        ("OtherTransaction/Function/_target_application:resolve_hello", 1),
        ("Function/_target_application:resolve_hello", 1),
    ]
    if is_graphql_2:
        _test_basic_metrics.append(("Function/graphql.execution.executor:execute", 1))
    else:  # GraphQL 3+
        _test_basic_metrics.append(("Function/graphql.execution.execute:execute", 1))

    @validate_transaction_metrics(
        "_target_application:resolve_hello",
        rollup_metrics=_test_basic_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        response = graphql_run(app, "{ hello }")
        assert not response.errors
        assert "Hello!" in str(response.data)
    _test()


def test_middleware(app, graphql_run, is_graphql_2):
    _test_middleware_metrics = [
        ("OtherTransaction/all", 1),
        ("OtherTransaction/Function/_target_application:resolve_hello", 1),
        ("Function/_target_application:resolve_hello", 1),
        ("Function/test_application:example_middleware", "present"),  # 2?????
    ]
    if is_graphql_2:
        _test_middleware_metrics.append(("Function/graphql.execution.executor:execute", 1))
    else:  # GraphQL 3+
        _test_middleware_metrics.append(("Function/graphql.execution.execute:execute", 1))

    @validate_transaction_metrics(
        "_target_application:resolve_hello",
        rollup_metrics=_test_middleware_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        response = graphql_run(app, "{ hello }", middleware=[example_middleware])
        assert not response.errors
        assert "Hello!" in str(response.data)
    _test()


def test_exception_in_middleware(app, graphql_run):
    @validate_transaction_errors(errors=_test_runtime_error)
    @background_task()
    def _test():
        response = graphql_run(app, "{ hello }", middleware=[error_middleware])
        assert response.errors

    _test()

def test_exception_in_resolver(app, graphql_run):
    @validate_transaction_errors(errors=_test_runtime_error)
    @background_task()
    def _test():
        response = graphql_run(app, "{ error }")
        assert response.errors

    _test()

def test_exception_in_validation(app, graphql_run):
    @validate_transaction_errors(errors=_test_runtime_error)
    @background_task()
    def _test():
        response = graphql_run(app, "{ missing_field }")
        assert response.errors

    _test()
