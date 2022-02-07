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

import gc
import grpc
import pytest
import random

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)
from testing_support.mock_external_grpc_aio_server import MockExternalgRPCAIOServer
import newrelic.packages.six as six

_coverage_source = [
    'newrelic.hooks.framework_grpcaio',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_grpcaio)',
        default_settings=_default_settings)


@pytest.fixture(scope='session')
async def grpc_app_server():
    async with MockExternalgRPCAIOServer(port=55555) as server:
        yield server, server.port


@pytest.fixture(scope='session')
async def mock_grpc_server(grpc_app_server):
    from sample_application.sample_application_pb2_grpc import (
            add_SampleApplicationServicer_to_server)
    from sample_application import SampleApplicationServicer
    server, port = grpc_app_server
    add_SampleApplicationServicer_to_server(
            SampleApplicationServicer(), server)
    return port


@pytest.fixture(scope='function', autouse=True)
def gc_garbage_empty():
    yield


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    return asyncio.get_event_loop()


@pytest.fixture(scope="session")
async def stub(stub_and_channel):
    stub_and_channel = stub_and_channel
    return stub_and_channel[0]


@pytest.fixture(scope="session")
async def stub_and_channel(mock_grpc_server):
    port = mock_grpc_server
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)

    stub, channel = create_stub_and_channel(port)
    async with channel:
        yield stub, channel

def create_stub_and_channel(port):
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)

    channel = grpc.aio.insecure_channel('localhost:%s' % port)
    stub = SampleApplicationStub(channel)
    return stub, channel
