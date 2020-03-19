from newrelic.core.data_collector import ApplicationSession
from newrelic.common.streaming_utils import TerminatingDeque
from newrelic.core.config import finalize_application_settings


def test_stream_connect(mock_grpc_server):
    settings = finalize_application_settings(
        {'mtb.endpoint': 'http://localhost:%d' % mock_grpc_server}
    )
    session = ApplicationSession('http://', settings.license_key, settings)
    stream_deque = TerminatingDeque(0)
    responses = session.connect_span_stream(stream_deque)
    stream_deque.shutdown()
    responses = list(responses)
    assert len(responses) == 1
    assert responses[0].messages_seen == 0
    # Calling shutdown will terminate the RPC
    session.shutdown_span_stream()
