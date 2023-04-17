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
import time

import pytest
from testing_support.fixtures import override_generic_settings
from testing_support.util import conditional_decorator
from testing_support.validators.validate_metric_payload import validate_metric_payload

from newrelic.common.streaming_utils import StreamBuffer
from newrelic.core.agent_streaming import StreamingRpc
from newrelic.core.application import Application
from newrelic.core.config import global_settings
from newrelic.core.infinite_tracing_pb2 import AttributeValue, Span
from newrelic.packages import six

settings = global_settings()

CONDITION_CLS = type(threading.Condition())


@pytest.fixture()
def app():
    app = Application("Python Agent Test (Infinite Tracing)")
    yield app
    # Calling internal_agent_shutdown on an application that is already closed
    # will raise an exception.
    active_session = app._active_session
    try:
        app.internal_agent_shutdown(restart=False)
    except:
        pass
    if active_session and active_session._rpc is not None:
        assert not active_session._rpc.response_processing_thread.is_alive()
        assert not active_session._rpc.channel


@pytest.mark.parametrize(
    "status_code, metrics",
    (
        (
            "UNIMPLEMENTED",
            [
                ("Supportability/InfiniteTracing/Span/gRPC/UNIMPLEMENTED", 1),
                ("Supportability/InfiniteTracing/Span/Response/Error", 1),
            ],
        ),
        (
            "INTERNAL",
            [
                ("Supportability/InfiniteTracing/Span/gRPC/INTERNAL", 1),
                ("Supportability/InfiniteTracing/Span/Response/Error", 1),
            ],
        ),
    ),
)
def test_infinite_tracing_span_streaming(mock_grpc_server, status_code, metrics, monkeypatch, app, batching):
    event = threading.Event()

    class TerminateOnWait(CONDITION_CLS):
        def notify_all(self, *args, **kwargs):
            event.set()
            return super(TerminateOnWait, self).notify_all(*args, **kwargs)

        def wait(self, *args, **kwargs):
            event.set()
            return super(TerminateOnWait, self).wait(*args, **kwargs)

    @staticmethod
    def condition(*args, **kwargs):
        return TerminateOnWait(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, "condition", condition)

    span = Span(
        intrinsics={"status_code": AttributeValue(string_value=status_code)}, agent_attributes={}, user_attributes={}
    )

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
        },
    )
    @validate_metric_payload(metrics)
    def _test():
        app.connect_to_data_collector(None)

        app._stats_engine.span_stream.put(span)

        assert event.wait(timeout=5)

        app.harvest(shutdown=True)

    _test()


def test_reconnect_on_failure(monkeypatch, mock_grpc_server, buffer_empty_event, app, batching):
    status_code = "INTERNAL"
    wait_event = threading.Event()
    continue_event = threading.Event()

    class WaitOnWait(CONDITION_CLS):
        def wait(self, *args, **kwargs):
            wait_event.set()
            continue_event.wait()
            return True

    @staticmethod
    def condition(*args, **kwargs):
        return WaitOnWait(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, "condition", condition)

    terminating_span = Span(
        intrinsics={"status_code": AttributeValue(string_value=status_code)}, agent_attributes={}, user_attributes={}
    )

    span = Span(intrinsics={}, agent_attributes={}, user_attributes={})

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
        },
    )
    def _test():
        app.connect_to_data_collector(None)

        # Send a span that will trigger a failure
        app._stats_engine.span_stream.put(terminating_span)

        assert wait_event.wait(timeout=5)

        # Send a normal span afterwards
        app._stats_engine.span_stream.put(span)

        buffer_empty_event.clear()

        # Trigger the event so that a reconnect will occur
        continue_event.set()

        # Wait for the stream buffer to empty meaning all spans have been sent.
        assert buffer_empty_event.wait(10)
        app.internal_agent_shutdown(restart=False)

    _test()


def test_agent_restart(app):
    # Get the application connected to the actual 8T endpoint
    app.connect_to_data_collector(None)
    rpc = app._active_session._rpc

    # Store references to the original rpc and threads
    original_rpc = rpc.rpc
    original_thread = rpc.response_processing_thread
    original_span_stream = app._stats_engine.span_stream
    assert original_rpc
    assert rpc.response_processing_thread.is_alive()

    # Force an agent restart
    app.internal_agent_shutdown(restart=True)

    # Wait for connect to complete
    app._connected_event.wait()
    rpc = app._active_session._rpc

    assert not original_thread.is_alive()
    assert rpc.rpc is not original_rpc
    assert app._stats_engine.span_stream is not original_span_stream
    assert rpc.response_processing_thread.is_alive()


def test_disconnect_on_UNIMPLEMENTED(mock_grpc_server, monkeypatch, app, batching):
    event = threading.Event()

    class WaitOnNotify(CONDITION_CLS):
        def notify_all(self, *args, **kwargs):
            event.set()
            return super(WaitOnNotify, self).notify_all(*args, **kwargs)

    @staticmethod
    def condition(*args, **kwargs):
        return WaitOnNotify(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, "condition", condition)

    terminating_span = Span(
        intrinsics={"status_code": AttributeValue(string_value="UNIMPLEMENTED")},
        agent_attributes={},
        user_attributes={},
    )

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
        },
    )
    def _test():
        app.connect_to_data_collector(None)

        # Send a span that will trigger disconnect
        app._stats_engine.span_stream.put(terminating_span)

        # Wait for the notify event in close to be called
        assert event.wait(timeout=5)

        # Verify the rpc management thread is killed
        rpc_thread = app._active_session._rpc.response_processing_thread
        rpc_thread.join(timeout=5)
        assert not rpc_thread.is_alive()

    _test()


def test_agent_shutdown():
    # Get the application connected to the actual 8T endpoint
    app = Application("Python Agent Test (Infinite Tracing)")
    app.connect_to_data_collector(None)
    rpc = app._active_session._rpc
    # Store references to the original rpc and threads
    assert rpc.response_processing_thread.is_alive()
    app.internal_agent_shutdown(restart=False)
    assert not rpc.response_processing_thread.is_alive()
    assert not rpc.channel


@pytest.mark.xfail(reason="This test is flaky", strict=False)
def test_no_delay_on_ok(mock_grpc_server, monkeypatch, app, batching):
    wait_event = threading.Event()
    connect_event = threading.Event()

    metrics = [
        ("Supportability/InfiniteTracing/Span/gRPC/OK", 1),
        ("Supportability/InfiniteTracing/Span/Response/Error", None),
    ]

    class SetFlagOnWait(CONDITION_CLS):
        def __init__(self, event, *args, **kwargs):
            super(SetFlagOnWait, self).__init__(*args, **kwargs)
            self.event = event

        def wait(self, *args, **kwargs):
            self.event.set()
            return super(SetFlagOnWait, self).wait(*args, **kwargs)

    @staticmethod
    def condition(*args, **kwargs):
        return SetFlagOnWait(wait_event, *args, **kwargs)

    _create_channel = StreamingRpc.create_channel

    def create_channel(self, *args, **kwargs):
        ret = _create_channel(self, *args, **kwargs)
        connect_event.set()
        return ret

    monkeypatch.setattr(StreamingRpc, "condition", condition)
    monkeypatch.setattr(StreamingRpc, "create_channel", create_channel)

    span = Span(
        intrinsics={"status_code": AttributeValue(string_value="OK")},
        agent_attributes={},
        user_attributes={},
    )

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
        },
    )
    @validate_metric_payload(metrics)
    def _test():
        def connect_complete():
            connect_event.set()

        app.connect_to_data_collector(connect_complete)

        assert connect_event.wait(timeout=5)
        connect_event.clear()

        # Send a span that will trigger disconnect
        stream_buffer = app._stats_engine.span_stream
        rpc = app._active_session._rpc

        # Put a span that will trigger an OK status code and wait for an attempted
        # reconnect.
        stream_buffer.put(span)
        assert connect_event.wait(timeout=5)
        rpc.close()
        assert not wait_event.is_set()
        app.harvest()

    _test()


@conditional_decorator(
    condition=six.PY2, decorator=pytest.mark.xfail(reason="Test frequently times out on Py2.", strict=False)
)
def test_no_data_loss_on_reconnect(mock_grpc_server, app, buffer_empty_event, batching, spans_processed_event):
    """
    Test for data loss when channel is closed by the server while waiting for more data in a request iterator.

    This is a bug that's caused by the periodic (15 second) disconnects issued by the trace observer. To observe,
    wait long enough in __next__'s notify.wait() call until the server issues a grpc.StatusCode.OK causing a
    disconnect and reconnect. Alternatively in the case of this test, we use a mock server to issue one at the
    appropriate moment rather than waiting for a real trace observer to issue a disconnect.

    While in this state, the very next span placed in the StreamBuffer would wake up the request_iterator for the
    now closed channel (which was waiting in the __next__ function) and be consumed. The channel, being closed,
    would discard the data and finish shutting down. This is now prevented by guards checking if the channel is
    closed before popping any data inside the request iterator, which instead raises a StopIteration.

    Relevant GitHub issue: https://github.com/grpc/grpc/issues/29110
    """

    terminating_span = Span(
        intrinsics={"wait_then_ok": AttributeValue(string_value="OK")}, agent_attributes={}, user_attributes={}
    )

    span = Span(intrinsics={}, agent_attributes={}, user_attributes={})

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
        },
    )
    def _test():
        # Connect to app and retrieve references to various components
        app.connect_to_data_collector(None)

        stream_buffer = app._stats_engine.span_stream
        rpc = app._active_session._rpc
        request_iterator = rpc.request_iterator

        # Wait until iterator is waiting on spans
        assert buffer_empty_event.wait(timeout=5)
        buffer_empty_event.clear()

        # Send a span that will trigger disconnect
        stream_buffer.put(terminating_span)

        # Wait for spans to be processed by server
        assert spans_processed_event.wait(timeout=5)
        spans_processed_event.clear()

        # Wait for OK status code to close the channel
        start_time = time.time()
        while not (request_iterator._stream and request_iterator._stream.done()):
            assert time.time() - start_time < 5, "Timed out waiting for OK status code."
            time.sleep(0.5)

        # Put new span and wait until buffer has been emptied and either sent or lost
        stream_buffer.put(span)
        assert spans_processed_event.wait(timeout=5), "Data lost in stream buffer iterator."

    _test()


@pytest.mark.parametrize("dropped_spans", [0, 1])
def test_span_supportability_metrics(mock_grpc_server, monkeypatch, app, dropped_spans, batching):
    wait_event = threading.Event()
    continue_event = threading.Event()

    total_spans = 3
    metrics = [
        ("Supportability/InfiniteTracing/Span/Seen", total_spans),
        (
            "Supportability/InfiniteTracing/Span/Sent",
            (total_spans - dropped_spans) or None,
        ),  # Replace 0 with None to indicate metric will not be sent
    ]

    class WaitOnWait(CONDITION_CLS):
        def wait(self, *args, **kwargs):
            wait_event.set()
            ret = super(WaitOnWait, self).wait(*args, **kwargs)
            assert continue_event.wait(timeout=5)
            return ret

    @staticmethod
    def condition(*args, **kwargs):
        return WaitOnWait(*args, **kwargs)

    monkeypatch.setattr(StreamBuffer, "condition", condition)

    span = Span(
        intrinsics={},
        agent_attributes={},
        user_attributes={},
    )

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": "localhost",
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
            "infinite_tracing.span_queue_size": total_spans - dropped_spans,
        },
    )
    @validate_metric_payload(metrics)
    def _test():
        app.connect_to_data_collector(None)

        assert wait_event.wait(timeout=5)

        stream_buffer = app._stats_engine.span_stream

        # Put enough spans to overflow buffer
        for _ in range(total_spans):
            stream_buffer.put(span)

        # Harvest all spans simultaneously
        wait_event.clear()
        continue_event.set()
        assert wait_event.wait(timeout=5)
        wait_event.clear()

        app.harvest()

    _test()


@pytest.mark.parametrize("trace_observer_host", ["localhost", None])
@pytest.mark.parametrize("batching", [True, False])
@pytest.mark.parametrize("compression", [True, False])
def test_settings_supportability_metrics(mock_grpc_server, app, trace_observer_host, batching, compression):
    connect_event = threading.Event()

    enabled = bool(trace_observer_host)

    metrics = [
        ("Supportability/InfiniteTracing/gRPC/Batching/enabled", 1 if enabled and batching else None),
        ("Supportability/InfiniteTracing/gRPC/Batching/disabled", 1 if enabled and not batching else None),
        ("Supportability/InfiniteTracing/gRPC/Compression/enabled", 1 if enabled and compression else None),
        ("Supportability/InfiniteTracing/gRPC/Compression/disabled", 1 if enabled and not compression else None),
    ]

    @override_generic_settings(
        settings,
        {
            "distributed_tracing.enabled": True,
            "span_events.enabled": True,
            "infinite_tracing.trace_observer_host": trace_observer_host,
            "infinite_tracing.trace_observer_port": mock_grpc_server,
            "infinite_tracing.ssl": False,
            "infinite_tracing.batching": batching,
            "infinite_tracing.compression": compression,
        },
    )
    @validate_metric_payload(metrics)
    def _test():
        def connect_complete():
            connect_event.set()

        app.connect_to_data_collector(connect_complete)

        assert connect_event.wait(timeout=5)
        connect_event.clear()

        app.harvest()

    _test()
