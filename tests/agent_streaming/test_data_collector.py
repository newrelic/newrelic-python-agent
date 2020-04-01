from newrelic.core.data_collector import ApplicationSession
from newrelic.common.streaming_utils import StreamBuffer
from newrelic.core.config import finalize_application_settings


def test_stream_connect(mock_grpc_server):
    settings = finalize_application_settings(
        {'infinite_tracing.trace_observer_url':
        'http://localhost:%d' % mock_grpc_server}
    )
    session = ApplicationSession('http://', settings.license_key, settings)
    stream_buffer = StreamBuffer(0)
    responses = session.connect_span_stream(stream_buffer)
    # Calling shutdown will terminate the RPC
    session.shutdown_span_stream()
