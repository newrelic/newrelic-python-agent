import mock

from newrelic.common.utilization import AWSVendorInfo
from newrelic.packages import requests


class MockResponse(object):

    def __init__(self, code, body, charset=None):
        self.code = code
        self.body = body
        self.charset = charset or 'iso-8859-1'
        self.headers = self._headers(self.charset)

    def _headers(self, charset):
        if self.charset.lower() == 'iso-8859-1':
            headers = {'content-type': 'text/plain'}
        else:
            headers = {'content-type': 'text/plain; charset=%s' % charset}
        return headers

    def read(self):
        return self.body.encode(self.charset)

def test_aws_vendor_info():
    aws = AWSVendorInfo()
    assert isinstance(aws, AWSVendorInfo)

def test_metadata_url():
    aws = AWSVendorInfo()
    url = aws.metadata_url('instance-id')
    assert url == 'http://169.254.169.254/2008-02-01/meta-data/instance-id'

@mock.patch.object(requests.Session, 'get')
def test_fetch(mock_get):
    mock_response = MockResponse('200', 'blah', 'utf-8')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    resp = aws.fetch('foo')
    assert resp == b'blah'

@mock.patch.object(requests.Session, 'get')
def test_instance_id(mock_get):
    mock_response = MockResponse('200', 'i-e7e85ce1', 'utf-8')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_id == b'i-e7e85ce1'
    mock_get.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-id',
            timeout=aws.timeout)

@mock.patch.object(requests.Session, 'get')
def test_instance_type(mock_get):
    mock_response = MockResponse('200', 'm3.medium', 'iso-8859-1')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_type == b'm3.medium'
    mock_get.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-type',
            timeout=aws.timeout)

@mock.patch.object(requests.Session, 'get')
def test_availability_zone(mock_get):
    mock_response = MockResponse('200', 'us-west-2b')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.availability_zone == b'us-west-2b'
    mock_get.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/placement/availability-zone',
            timeout=aws.timeout)

@mock.patch.object(requests.Session, 'get')
def test_fetch_connect_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectTimeout

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None

@mock.patch.object(requests.Session, 'get')
def test_fetch_read_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.ReadTimeout

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None

@mock.patch.object(requests.Session, 'get')
def test_fetch_exception(mock_get):
    mock_get.side_effect = Exception

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None
