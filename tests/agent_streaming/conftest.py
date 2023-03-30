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

import threading

import pytest

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611
from testing_support.mock_external_grpc_server import MockExternalgRPCServer

from newrelic.common.streaming_utils import StreamBuffer

CONDITION_CLS = type(threading.Condition())


_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
    "agent_limits.errors_per_harvest": 100,
    "distributed_tracing.enabled": True,
    "infinite_tracing.trace_observer_host": "nr-internal.aws-us-east-2.tracing.staging-edge.nr-data.net",
    "infinite_tracing.compression": True,
    "debug.connect_span_stream_in_developer_mode": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (agent_streaming)", default_settings=_default_settings
)


@pytest.fixture(scope="module")
def grpc_app_server():
    with MockExternalgRPCServer() as server:
        yield server, server.port


@pytest.fixture(scope="module")
def mock_grpc_server(grpc_app_server):
    from _test_handler import HANDLERS

    server, port = grpc_app_server
    server.add_generic_rpc_handlers(HANDLERS)
    return port


class SetEventOnWait(CONDITION_CLS):
    def __init__(self, event, *args, **kwargs):
        super(SetEventOnWait, self).__init__(*args, **kwargs)
        self._event = event

    def wait(self, *args, **kwargs):
        self._event.set()
        return super(SetEventOnWait, self).wait(*args, **kwargs)


@pytest.fixture(scope="function")
def buffer_empty_event(monkeypatch):
    event = threading.Event()

    @staticmethod
    def condition(*args, **kwargs):
        return SetEventOnWait(event, *args, **kwargs)

    monkeypatch.setattr(StreamBuffer, "condition", condition)
    return event


@pytest.fixture(scope="session", params=[pytest.param(True, id="batching"), pytest.param(False, id="nonbatching")])
def batching(request):
    return request.param


@pytest.fixture(scope="function")
def spans_received():
    from _test_handler import SPANS_RECEIVED

    SPANS_RECEIVED.clear()
    return SPANS_RECEIVED


@pytest.fixture(scope="function")
def span_batches_received():
    from _test_handler import SPAN_BATCHES_RECEIVED

    SPAN_BATCHES_RECEIVED.clear()
    return SPAN_BATCHES_RECEIVED


@pytest.fixture(scope="function")
def spans_processed_event():
    from _test_handler import SPANS_PROCESSED_EVENT

    SPANS_PROCESSED_EVENT.clear()
    return SPANS_PROCESSED_EVENT
