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

import six
import grpc
import pytest
from conftest import create_stub_and_channel
from _test_common import create_request, wait_for_transaction_completion
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_event_attributes, override_application_settings,
        override_generic_settings, function_not_called,
        validate_transaction_errors)


def select_python_version(py2, py3):
    return six.PY3 and py3 or py2


if hasattr(grpc, '__version__'):
    GRPC_VERSION = tuple(int(v) for v in grpc.__version__.split('.'))
else:
    GRPC_VERSION = None

_test_matrix = ["method_name,streaming_request", [
    ("DoUnaryUnary", False),
    ("DoUnaryStream", False),
    ("DoStreamUnary", True),
    ("DoStreamStream", True)
]]


@pytest.mark.parametrize(*_test_matrix)
def test_simple(method_name, streaming_request, mock_grpc_server, stub):
    port = mock_grpc_server
    request = create_request(streaming_request)
    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)

    @validate_transaction_metrics(_transaction_name)
    @override_application_settings({'attributes.include': ['request.*']})
    @validate_transaction_event_attributes(
            required_params={
                'agent': ['request.uri', 'request.headers.userAgent',
                    'response.status', 'response.headers.contentType'],
                'user': [],
                'intrinsic': ['port'],
            },
            exact_attrs={
                'agent': {},
                'user': {},
                'intrinsic': {'port': port}
            })
    @wait_for_transaction_completion
    def _doit():
        response = method(request)

        try:
            list(response)
        except Exception:
            pass

    _doit()


@pytest.mark.parametrize(*_test_matrix)
def test_raises_response_status(method_name, streaming_request,
        mock_grpc_server, stub):
    port = mock_grpc_server
    request = create_request(streaming_request)

    method_name = method_name + 'Raises'

    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)

    status_code = str(grpc.StatusCode.UNKNOWN.value[0])

    @validate_transaction_errors(errors=[select_python_version(
        py2='exceptions:AssertionError', py3='builtins:AssertionError')])
    @validate_transaction_metrics(_transaction_name)
    @override_application_settings({'attributes.include': ['request.*']})
    @validate_transaction_event_attributes(
            required_params={
                'agent': ['request.uri', 'request.headers.userAgent',
                    'response.status'],
                'user': [],
                'intrinsic': ['port'],
            },
            exact_attrs={
                'agent': {'response.status': status_code},
                'user': {},
                'intrinsic': {'port': port}
            })
    @wait_for_transaction_completion
    def _doit():
        try:
            response = method(request)
            list(response)
        except Exception:
            pass

    _doit()


@pytest.mark.parametrize(*_test_matrix)
def test_abort(method_name, streaming_request, mock_grpc_server, stub):
    port = mock_grpc_server
    request = create_request(streaming_request)
    method = getattr(stub, method_name + 'Abort')

    @validate_transaction_errors(errors=[select_python_version(
        py2='exceptions:Exception', py3='builtins:Exception')])
    @wait_for_transaction_completion
    def _doit():
        with pytest.raises(grpc.RpcError) as error:
            response = method(request)
            list(response)

        assert error.value.details() == 'aborting'
        assert error.value.code() == grpc.StatusCode.ABORTED

    _doit()


@pytest.mark.parametrize(*_test_matrix)
def test_abort_with_status(method_name, streaming_request, mock_grpc_server, stub):
    port = mock_grpc_server
    request = create_request(streaming_request)
    method = getattr(stub, method_name + 'AbortWithStatus')

    @validate_transaction_errors(errors=[select_python_version(
        py2='exceptions:Exception', py3='builtins:Exception')])
    @wait_for_transaction_completion
    def _doit():
        with pytest.raises(grpc.RpcError) as error:
            response = method(request)
            list(response)

        assert error.value.details() == 'abort_with_status'
        assert error.value.code() == grpc.StatusCode.ABORTED

    _doit()


def test_no_exception_client_close(mock_grpc_server):
    port = mock_grpc_server
    # We can't use the stub_and_channel fixture here as closing 
    # that channel will cause any subsequent tests to fail.
    # Instead we create a brand new channel to close.
    stub, channel = create_stub_and_channel(port)

    with channel:
        request = create_request(False, timesout=True)

        method = getattr(stub, 'DoUnaryUnary')

        @validate_transaction_errors(errors=[])
        @wait_for_transaction_completion
        def _doit():
            future_response = method.future(request)
            channel.close()
            with pytest.raises(grpc.RpcError) as error:
                future_response.result()

            assert error.value.code() == grpc.StatusCode.CANCELLED

        _doit()


def test_newrelic_disabled_no_transaction(mock_grpc_server, stub):
    port = mock_grpc_server
    request = create_request(False)

    method = getattr(stub, 'DoUnaryUnary')

    @override_generic_settings(global_settings(), {'enabled': False})
    @function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
    @wait_for_transaction_completion
    def _doit():
        method(request)

    _doit()
