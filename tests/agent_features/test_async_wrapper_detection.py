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
import time

import pytest
from testing_support.fixtures import capture_transaction_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.graphql_trace import graphql_operation_trace, graphql_resolver_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace
from newrelic.common.async_wrapper import generator_wrapper

trace_metric_cases = [
    (functools.partial(function_trace, name="simple_gen"), "Function/simple_gen"),
    (functools.partial(external_trace, library="lib", url="http://foo.com"), "External/foo.com/lib/"),
    (functools.partial(database_trace, "select * from foo"), "Datastore/statement/None/foo/select"),
    (functools.partial(datastore_trace, "lib", "foo", "bar"), "Datastore/statement/lib/foo/bar"),
    (functools.partial(message_trace, "lib", "op", "typ", "name"), "MessageBroker/lib/typ/op/Named/name"),
    (functools.partial(memcache_trace, "cmd"), "Memcache/cmd"),
    (functools.partial(graphql_operation_trace), "GraphQL/operation/GraphQL/<unknown>/<anonymous>/<unknown>"),
    (functools.partial(graphql_resolver_trace), "GraphQL/resolve/GraphQL/<unknown>"),
]


@pytest.mark.parametrize("trace,metric", trace_metric_cases)
def test_automatic_generator_trace_wrapper(trace, metric):
    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
        "test_automatic_generator_trace_wrapper",
        background_task=True,
        scoped_metrics=[(metric, 1)],
        rollup_metrics=[(metric, 1)],
    )
    @background_task(name="test_automatic_generator_trace_wrapper")
    def _test():
        @trace()
        def gen():
            time.sleep(0.1)
            yield
            time.sleep(0.1)

        for _ in gen():
            pass

    _test()

    # Check that generators time the total call time (including pauses)
    metric_key = (metric, "")
    assert full_metrics[metric_key].total_call_time >= 0.2


@pytest.mark.parametrize("trace,metric", trace_metric_cases)
def test_manual_generator_trace_wrapper(trace, metric):
    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
        "test_automatic_generator_trace_wrapper",
        background_task=True,
        scoped_metrics=[(metric, 1)],
        rollup_metrics=[(metric, 1)],
    )
    @background_task(name="test_automatic_generator_trace_wrapper")
    def _test():
        @trace(async_wrapper=generator_wrapper)
        def wrapper_func():
            """Function that returns a generator object, obscuring the automatic introspection of async_wrapper()"""

            def gen():
                time.sleep(0.1)
                yield
                time.sleep(0.1)

            return gen()

        for _ in wrapper_func():
            pass

    _test()

    # Check that generators time the total call time (including pauses)
    metric_key = (metric, "")
    assert full_metrics[metric_key].total_call_time >= 0.2
