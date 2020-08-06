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

from newrelic.core.agent_streaming import StreamingRpc
from newrelic.common.streaming_utils import StreamBuffer
from newrelic.core.infinite_tracing_pb2 import Span, AttributeValue


CONDITION_CLS = type(threading.Condition())
DEFAULT_METADATA = (("agent_run_token", ""), ("license_key", ""))


def record_metric(*args, **kwargs):
    pass


def test_close_before_connect(mock_grpc_server):
    endpoint = "localhost:%s" % mock_grpc_server
    stream_buffer = StreamBuffer(0)

    rpc = StreamingRpc(
        endpoint, stream_buffer, DEFAULT_METADATA, record_metric, ssl=False
    )

    # Calling close will close the grpc channel
    rpc.close()
    rpc.connect()
    # The response processing thread should immediately exit if the channel is
    # closed
    rpc.response_processing_thread.join(timeout=5)
    assert not rpc.response_processing_thread.is_alive()


def test_close_while_connected(mock_grpc_server, buffer_empty_event):
    endpoint = "localhost:%s" % mock_grpc_server
    stream_buffer = StreamBuffer(1)

    rpc = StreamingRpc(
        endpoint, stream_buffer, DEFAULT_METADATA, record_metric, ssl=False
    )

    rpc.connect()
    # Check the processing thread is alive and spans are being sent
    assert rpc.response_processing_thread.is_alive()

    span = Span(intrinsics={}, agent_attributes={}, user_attributes={})

    buffer_empty_event.clear()
    stream_buffer.put(span)

    assert buffer_empty_event.wait(5)

    rpc.close()
    assert not rpc.response_processing_thread.is_alive()


def test_close_while_awaiting_reconnect(mock_grpc_server, monkeypatch):
    event = threading.Event()

    class WaitOnWait(CONDITION_CLS):
        def wait(self, *args, **kwargs):
            event.set()
            # Call super wait with no arguments to block until a notify
            return super(WaitOnWait, self).wait()

    @staticmethod
    def condition(*args, **kwargs):
        return WaitOnWait(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, "condition", condition)

    span = Span(
        intrinsics={"status_code": AttributeValue(string_value="INTERNAL")},
        agent_attributes={},
        user_attributes={},
    )

    endpoint = "localhost:%s" % mock_grpc_server
    stream_buffer = StreamBuffer(1)

    rpc = StreamingRpc(
        endpoint, stream_buffer, DEFAULT_METADATA, record_metric, ssl=False
    )

    rpc.connect()
    # Send a span to trigger reconnect
    stream_buffer.put(span)
    # Wait until for StreamingRpc to pause before attempting reconnect
    assert event.wait(timeout=5)
    # Close the rpc
    rpc.close()
    # Make sure the processing_thread is closed
    assert not rpc.response_processing_thread.is_alive()
