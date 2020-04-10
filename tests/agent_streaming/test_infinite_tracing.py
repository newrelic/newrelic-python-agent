import pytest
import threading
import time

from newrelic.core.config import global_settings
from testing_support.fixtures import override_generic_settings

from newrelic.core.application import Application
from newrelic.api.application import application_instance
from newrelic.core.data_collector import StreamingRpc
from newrelic.core.infinite_tracing_pb2 import Span, AttributeValue
from testing_support.validators.validate_metric_payload import (
    validate_metric_payload)

settings = global_settings()

CONDITION_CLS = type(threading.Condition())


@pytest.mark.parametrize(
     'status_code, metrics', (
     ('UNIMPLEMENTED', [
            ('Supportability/InfiniteTracing/Span/gRPC/UNIMPLEMENTED', 1),
            ('Supportability/InfiniteTracing/Span/Response/Error', 1)]),
     ('INTERNAL', [
            ('Supportability/InfiniteTracing/Span/gRPC/INTERNAL', 1),
            ('Supportability/InfiniteTracing/Span/Response/Error', 1)]),
     ('OK', [
            ('Supportability/InfiniteTracing/Span/gRPC/OK', 1),
            ('Supportability/InfiniteTracing/Span/Response/Error', None)]),
 ))
def test_infinite_tracing_span_streaming(mock_grpc_server,
        status_code, metrics, monkeypatch):
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

    monkeypatch.setattr(StreamingRpc, 'condition', condition)

    span = Span(
        intrinsics={'status_code': AttributeValue(string_value=status_code)},
        agent_attributes={},
        user_attributes={})

    @override_generic_settings(settings, {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'infinite_tracing.trace_observer_host': 'localhost',
        'infinite_tracing.trace_observer_port': mock_grpc_server,
        'infinite_tracing.ssl': False,
    })
    @validate_metric_payload(metrics=metrics)
    def _test():
        app = Application('Python Agent Test (Infinite Tracing)')
        app.connect_to_data_collector(None)

        app._stats_engine.span_stream.put(span)

        assert event.wait(timeout=5)

        app.harvest(shutdown=True)

    _test()


@pytest.mark.parametrize('status_code', ('INTERNAL', 'OK'))
def test_reconnect_on_failure(status_code, monkeypatch, mock_grpc_server,
        buffer_empty_event):
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

    monkeypatch.setattr(StreamingRpc, 'condition', condition)

    terminating_span = Span(
        intrinsics={'status_code': AttributeValue(string_value=status_code)},
        agent_attributes={},
        user_attributes={})

    span = Span(
        intrinsics={},
        agent_attributes={},
        user_attributes={})

    @override_generic_settings(settings, {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'infinite_tracing.trace_observer_host': 'localhost',
        'infinite_tracing.trace_observer_port': mock_grpc_server,
        'infinite_tracing.ssl': False,
    })
    def _test():
        app = Application('Python Agent Test (Infinite Tracing)')
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


def test_agent_restart():
    # Get the application connected to the actual 8T endpoint
    app = Application('Python Agent Test (Infinite Tracing)')
    app.connect_to_data_collector(None)
    rpc = app._active_session._rpc
    # Store references to the orginal rpc and threads
    original_rpc = rpc.rpc
    original_thread = rpc.response_processing_thread
    assert original_rpc
    assert rpc.response_processing_thread.is_alive()
    # Force an agent restart
    app.internal_agent_shutdown(restart=True)
    # Wait for connect to complete
    app._connected_event.wait()
    rpc = app._active_session._rpc
    assert not original_thread.is_alive()
    assert rpc.rpc is not original_rpc
    assert rpc.response_processing_thread.is_alive()
    app.internal_agent_shutdown(restart=False)


def test_disconnect_on_UNIMPLEMENTED(mock_grpc_server, monkeypatch,
        buffer_empty_event):
    event = threading.Event()

    class WaitOnNotify(CONDITION_CLS):
        def notify_all(self, *args, **kwargs):
            event.set()
            return super(WaitOnNotify, self).notify_all(*args, **kwargs)

    @staticmethod
    def condition(*args, **kwargs):
        return WaitOnNotify(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, 'condition', condition)

    terminating_span = Span(
        intrinsics={'status_code': AttributeValue(
            string_value='UNIMPLEMENTED')},
        agent_attributes={},
        user_attributes={})

    span = Span(
        intrinsics={},
        agent_attributes={},
        user_attributes={})

    @override_generic_settings(settings, {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'infinite_tracing.trace_observer_host': 'localhost',
        'infinite_tracing.trace_observer_port': mock_grpc_server,
        'infinite_tracing.ssl': False,
    })
    def _test():
        app = Application('Python Agent Test (Infinite Tracing)')
        app.connect_to_data_collector(None)

        # Send a span that will trigger disconnect
        app._stats_engine.span_stream.put(terminating_span)

        # Wait for the notify event in close to be called
        assert event.wait(timeout=5)

        # Verify the rpc management thread is killed
        rpc_thread = app._active_session._rpc.response_processing_thread
        rpc_thread.join(timeout=5)
        assert not rpc_thread.is_alive()

        # Put a span in the queue after the connection closes
        app._stats_engine.span_stream.put(span)

        buffer_empty_event.clear()

        # Trigger an agent restart
        app.internal_agent_shutdown(restart=True)

        # Wait for the restart to complete
        app._connected_event.wait()

        # Check data was discarded during restart
        assert not app._stats_engine.span_stream._queue

        # Send a normal span to confirm reconnect occured with restart
        app._stats_engine.span_stream.put(span)

        # Wait for the stream buffer to empty meaning all spans have been sent.
        assert buffer_empty_event.wait(10)
        app.internal_agent_shutdown(restart=False)

    _test()


def test_agent_shutdown():
    # Get the application connected to the actual 8T endpoint
    app = Application('Python Agent Test (Infinite Tracing)')
    app.connect_to_data_collector(None)
    rpc = app._active_session._rpc
    # Store references to the orginal rpc and threads
    assert rpc.response_processing_thread.is_alive()
    app.internal_agent_shutdown(restart=False)
    assert not rpc.response_processing_thread.is_alive()
    assert not rpc.channel
