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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either exess or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

import grpc
import pytest
from conftest import create_stub_and_channel
from framework_grpc._test_common import create_request, wait_for_transaction_completion
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_event_attributes, override_application_settings,
        override_generic_settings, function_not_called,
        validate_transaction_errors)


if hasattr(grpc, '__version__'):
    GRPC_VERSION = tuple(int(v) for v in grpc.__version__.split('.'))
else:
    GRPC_VERSION = None


def test_newrelic_disabled_no_transaction(mock_grpc_server, stub):
    import asyncio

    loop = asyncio.get_event_loop()

    port = mock_grpc_server
    request = create_request(False)

    method = getattr(stub, 'DoUnaryUnary')

    @override_generic_settings(global_settings(), {'enabled': False})
    @function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
    @wait_for_transaction_completion
    def _doit():
        async def coro():
            c = method(request)
            await c._raise_for_status()
        loop.run_until_complete(coro())

    _doit()


_test_matrix = ["method_name,streaming_request", [
    ("DoUnaryUnary", False),
    ("DoUnaryStream", False),
    ("DoStreamUnary", True),
    ("DoStreamStream", True)
]]


@pytest.mark.parametrize(*_test_matrix)
def test_simple(method_name, streaming_request, mock_grpc_server, stub):
    import asyncio

    loop = asyncio.get_event_loop()

    port = mock_grpc_server
    request = create_request(streaming_request)
    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)
    breakpoint()

    @override_application_settings({'attributes.include': ['request.*']})
    # @validate_transaction_event_attributes(
    #         required_params={
    #             'agent': ['request.uri', 'request.headers.userAgent',
    #                 'response.status', 'response.headers.contentType'],
    #             'user': [],
    #             'intrinsic': ['port'],
    #         },
    #         exact_attrs={
    #             'agent': {},
    #             'user': {},
    #             'intrinsic': {'port': port}
    #         })
    @validate_transaction_metrics(_transaction_name)
    @wait_for_transaction_completion
    def _doit():
        async def coro():
            c = method(request)
            await c._raise_for_status()
    
            breakpoint()
            return c

        response = loop.run_until_complete(coro())
        assert re.match(r"\w+: Hello World", response.text), response.text

        try:
            list(response)
        except Exception:
            pass

    _doit()
