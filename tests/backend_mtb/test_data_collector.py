import json

from newrelic.core.data_collector import ApplicationSession
from newrelic.common.streaming_utils import TerminatingDeque
from newrelic.core.config import finalize_application_settings
import newrelic.packages.requests as requests


class FakeRequestsSession(requests.Session):
    def __init__(self, status, text):
        self.status = status
        self.text = text

    def request(self, *args, **kwargs):
        response = requests.Response()
        response.status_code = self.status
        response._content_consumed = True
        response._content = self.text.encode('utf-8')

        return response


def test_stream_connect(mock_grpc_server):
    settings = finalize_application_settings(
        {'mtb.endpoint': 'http://localhost:%d' % mock_grpc_server}
    )
    requests_session = FakeRequestsSession(
            200, json.dumps({'return_value': ''}))
    session = ApplicationSession('http://', settings.license_key, settings)
    session._requests_session = requests_session
    stream_deque = TerminatingDeque(0)
    responses = session.connect_span_stream(stream_deque)
    stream_deque.shutdown()
    responses = list(responses)
    assert len(responses) == 1
    assert responses[0].messages_seen == 0
    # Calling shutdown will terminate the RPC
    session.shutdown_span_stream()
