import mock
import threading
import time

from newrelic.packages import requests
from newrelic.packages.six.moves import BaseHTTPServer
from newrelic.common.utilization_common import CommonUtilization
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext


# Valid Length Tests

def test_simple_valid_length():
    data = '  HelloWorld  '
    assert CommonUtilization.valid_length(data)


def test_simple_invalid_length():
    data = '0' * 256
    assert not CommonUtilization.valid_length(data)


def test_unicode_valid_length():
    # unicode sailboat! (3 bytes)
    data = u'HelloWorld\u26F5'
    assert len(data) == 11
    assert CommonUtilization.valid_length(data)


def test_unicode_invalid_length():
    # unicode sailboat! (3 bytes)
    # this test checks that the unicode character is counted as 3 bytes instead
    # of 1
    data = u'0' * (256 - 3) + u'\u26F5'
    assert len(data) == (256 - 3 + 1)
    assert not CommonUtilization.valid_length(data)


def test_nonetype_length():
    assert not CommonUtilization.valid_length(None)


# Valid Chars Tests

def test_simple_valid_chars():
    data = '  Server1.machine_thing/metal-box  '
    assert CommonUtilization.valid_chars(data)


def test_simple_invalid_chars():
    data = 'Server1.costs.$$$$$$'
    assert not CommonUtilization.valid_chars(data)


def test_unicode_is_valid():
    data = u'HelloWorld\u26F5'
    assert CommonUtilization.valid_chars(data)


def test_nonetype_chars():
    assert not CommonUtilization.valid_chars(None)


# Normalize Tests

def test_normalize_no_strip():
    data = 'Hello World'
    result = CommonUtilization.normalize('thing', data)
    assert result == 'Hello World'


def test_normalize_strip():
    data = '         Hello World          '
    result = CommonUtilization.normalize('thing', data)
    assert result == 'Hello World'


def test_invalid_length_normalize():
    data = '0' * 256
    result = CommonUtilization.normalize('thing', data)
    assert result is None


def test_invalid_chars_normalize():
    data = u'$HelloWorld$'
    result = CommonUtilization.normalize('thing', data)
    assert result is None


def test_empty_after_strip_normalize():
    data = '          '
    result = CommonUtilization.normalize('thing', data)
    assert result is None


def test_non_str_normalize():
    data = 123
    result = CommonUtilization.normalize('thing', data)
    assert result is None


def test_nonetype_normalize():
    assert not CommonUtilization.normalize('pass', None)


# Test Error Reporting

def test_supportability_metric():
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        CommonUtilization.record_error('Resource', 'Data')

    assert 'Supportability/utilization//error' in internal_metrics


# Test fetch

class TimeoutHttpServer(threading.Thread):
    class ExternalHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(0.2)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Done')

    def __init__(self, *args, **kwargs):
        super(TimeoutHttpServer, self).__init__(*args, **kwargs)
        self.port = 8989
        self.httpd = BaseHTTPServer.HTTPServer(('localhost', 8989),
                self.ExternalHandler)
        self.daemon = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, tb):
        self.stop()

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        # Shutdowns the httpd server.
        self.httpd.shutdown()
        # Close the socket so we can reuse it.
        self.httpd.socket.close()
        self.join()


@mock.patch.object(requests.Session, 'get')
def test_fetch_success(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    mock_get.return_value = response

    resp = CommonUtilization.fetch()

    assert resp is response


@mock.patch.object(requests.Session, 'get')
def test_fetch_unsuccessful_http_status(mock_get):
    response = requests.models.Response()
    response.status_code = 404
    mock_get.return_value = response

    resp = CommonUtilization.fetch()

    assert resp is None


def test_fetch_timeout():
    class LocalhostUtilization(CommonUtilization):
        METADATA_URL = 'http://localhost:8989'
        TIMEOUT = 0.1

    with TimeoutHttpServer():
        resp = LocalhostUtilization.fetch()

    assert resp is None


# Test Get Values

def test_get_values_success():
    response = requests.models.Response()
    response.status_code = 200
    response._content = b'{"data": "check"}'

    vals = CommonUtilization.get_values(response)

    assert vals == {'data': 'check'}


def test_get_values_fail():
    response = requests.models.Response()
    response.status_code = 200
    response._content = b'{'

    vals = CommonUtilization.get_values(response)

    assert vals is None


def test_get_values_nonetype():
    assert not CommonUtilization().get_values(None)


# Test sanitize

def test_sanitize_success():
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    values = {'key1': 'x', 'key2': 'y', 'key3': 'z'}

    d = ExpectKey.sanitize(values)

    assert d == {'key1': 'x', 'key2': 'y'}


def test_sanitize_typical_fail():
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    values = {'key1': 'x', 'key3': 'z'}

    d = ExpectKey.sanitize(values)

    assert d is None


def test_sanitize_only_spaces_fail():
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    values = {'key1': 'x', 'key2': '       '}

    d = ExpectKey.sanitize(values)

    assert d is None


def test_sanitize_nonetype():
    assert not CommonUtilization().sanitize(None)


# Test detect

@mock.patch.object(requests.Session, 'get')
def test_detect_success(mock_get):
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    response = requests.models.Response()
    response.status_code = 200
    response._content = b'{"key1": "x", "key2": "y", "key3": "z"}'
    mock_get.return_value = response

    d = ExpectKey.detect()

    assert d == {'key1': 'x', 'key2': 'y'}


@mock.patch.object(requests.Session, 'get')
def test_detect_missing_key(mock_get):
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    response = requests.models.Response()
    response.status_code = 200
    response._content = b'{"key1": "x", "key3": "z"}'
    mock_get.return_value = response

    d = ExpectKey.detect()

    assert d is None


@mock.patch.object(requests.Session, 'get')
def test_detect_invalid_json(mock_get):
    class ExpectKey(CommonUtilization):
        EXPECTED_KEYS = ['key1', 'key2']

    response = requests.models.Response()
    response.status_code = 200
    response._content = b':-3'
    mock_get.return_value = response

    d = ExpectKey.detect()

    assert d is None
