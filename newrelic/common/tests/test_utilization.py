import mock

from newrelic.common.utilization import AWSVendorInfo
from newrelic.packages import requests


class MockResponse(object):

    def __init__(self, code, body):
        self.code = code
        self.text = body

def test_aws_vendor_info():
    aws = AWSVendorInfo()
    assert isinstance(aws, AWSVendorInfo)

def test_metadata_url():
    aws = AWSVendorInfo()
    url = aws.metadata_url('instance-id')
    assert url == 'http://169.254.169.254/2008-02-01/meta-data/instance-id'

@mock.patch.object(requests.Session, 'get')
def test_fetch(mock_get):
    mock_response = MockResponse('200', 'blah')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    resp = aws.fetch('foo')
    assert resp == 'blah'

@mock.patch.object(requests.Session, 'get')
def test_instance_id(mock_get):
    mock_response = MockResponse('200', 'i-e7e85ce1')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_id == 'i-e7e85ce1'
    mock_get.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-id',
            timeout=aws.timeout)

@mock.patch.object(requests.Session, 'get')
def test_instance_type(mock_get):
    mock_response = MockResponse('200', 'm3.medium')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_type == 'm3.medium'
    mock_get.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-type',
            timeout=aws.timeout)

@mock.patch.object(requests.Session, 'get')
def test_availability_zone(mock_get):
    mock_response = MockResponse('200', 'us-west-2b')
    mock_get.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.availability_zone == 'us-west-2b'
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

def test_normalize_strip_whitespace():
    assert AWSVendorInfo().normalize('instance_key', ' blah ') == 'blah'

def test_normalize_correct_length():
    assert AWSVendorInfo().normalize('instance_key', 'blah') == 'blah'

def test_normalize_too_long():
    data = 'x' * 256
    assert AWSVendorInfo().normalize('instance_key', data) == None

def test_normalize_ok_regex():
    data = '12345'
    assert AWSVendorInfo().normalize('instance_key', data) == data

def test_normalize_bad_regex():
    data = '!#$'
    assert AWSVendorInfo().normalize('instance_key', data) == None

def test_normalize_ok_unicode_range():
    data = u'\u2603'
    assert AWSVendorInfo().normalize('instance_key', data) == data

@mock.patch.object(requests.Session, 'get')
def test_to_dict(mock_get):
    mock_get.side_effect = [MockResponse('200', 'foo'),
            MockResponse('200', 'bar'),
            MockResponse('200', 'baz')]

    aws = AWSVendorInfo()
    assert aws.to_dict() == {'aws': {'id': 'foo', 'type': 'bar', 'zone': 'baz'}}
