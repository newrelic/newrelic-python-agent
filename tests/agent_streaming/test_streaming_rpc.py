import grpc
import threading

from newrelic.core.data_collector import StreamingRpc
from newrelic.common.streaming_utils import StreamBuffer
from newrelic.core.infinite_tracing_pb2 import Span, AttributeValue


CONDITION_CLS = type(threading.Condition())
DEFAULT_METADATA = (("agent_run_token", ""), ("license_key", ""))


def record_metric(*args, **kwargs):
    pass


def test_close_before_connect(mock_grpc_server):
    channel = grpc.insecure_channel("localhost:%s" % mock_grpc_server)
    stream_buffer = StreamBuffer(0)

    rpc = StreamingRpc(channel, stream_buffer, DEFAULT_METADATA, record_metric)

    # Calling close will close the grpc channel
    rpc.close()
    rpc.connect()
    # The response processing thread should immediatly exit if the channel is
    # closed
    rpc.response_processing_thread.join(timeout=5)
    assert not rpc.response_processing_thread.is_alive()


def test_close_while_connected(mock_grpc_server, buffer_empty_event):
    channel = grpc.insecure_channel("localhost:%s" % mock_grpc_server)
    stream_buffer = StreamBuffer(1)

    rpc = StreamingRpc(channel, stream_buffer, DEFAULT_METADATA, record_metric)

    rpc.connect()
    # Check the procesing thread is alive and spans are being sent
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

    monkeypatch.setattr(StreamingRpc, 'condition', condition)

    span = Span(
        intrinsics={"status_code": AttributeValue(string_value="INTERNAL")},
        agent_attributes={},
        user_attributes={},
    )

    channel = grpc.insecure_channel("localhost:%s" % mock_grpc_server)

    stream_buffer = StreamBuffer(1)

    rpc = StreamingRpc(channel, stream_buffer, DEFAULT_METADATA, record_metric)

    rpc.connect()
    # Send a span to trigger reconnect
    stream_buffer.put(span)
    # Wait until for StreamingRpc to pause before attempting reconnect
    assert event.wait(timeout=5)
    # Close the rpc
    rpc.close()
    # Make sure the processing_thread is closed
    assert not rpc.response_processing_thread.is_alive()
