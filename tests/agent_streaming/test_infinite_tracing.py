import pytest
import threading
import time

from newrelic.core.config import global_settings, finalize_application_settings
from testing_support.fixtures import (override_generic_settings,
         function_not_called, failing_endpoint)

from newrelic.core.application import Application
from newrelic.core.data_collector import StreamingRpc
from newrelic.core.infinite_tracing_pb2 import Span, AttributeValue
from testing_support.validators.validate_metric_payload import validate_metric_payload

settings = global_settings()


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
def test_infinite_tracing_span_streaming(mock_grpc_server, status_code, metrics, monkeypatch):
    event = threading.Event()

    class TerminateOnWait(threading.Condition):
        def notify_all(self, *args, **kwargs):
            event.set()
            return super(TerminateOnWait, self).notify_all(*args, **kwargs)

        def wait(self, *args, **kwargs):
            event.set()
            return super(TerminateOnWait, self).wait(*args, **kwargs)

    monkeypatch.setattr(StreamingRpc, 'CONDITION_CLS', TerminateOnWait)

    span = Span(
        intrinsics={'status_code': AttributeValue(string_value=status_code)},
        agent_attributes={},
        user_attributes={})

    @override_generic_settings(settings, {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'infinite_tracing.trace_observer_url': 'http://localhost:%s' % mock_grpc_server,
    })
    @validate_metric_payload(metrics=metrics)
    def _test():
        app = Application('Python Agent Test (Infinite Tracing)')
        app.connect_to_data_collector(None)

        app._stats_engine.span_stream.put(span)

        assert event.wait(timeout=5)

        app.harvest(shutdown=True)

    _test()