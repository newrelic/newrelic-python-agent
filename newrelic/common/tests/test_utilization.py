import mock
import socket
import urllib2

from newrelic.common.utilization import AWSVendorInfo


class MockResponse(object):

    def __init__(self, code, body):
        self.code = code
        self.body = body

    def read(self):
        return self.body

def test_aws_vendor_info():
    aws = AWSVendorInfo()
    assert isinstance(aws, AWSVendorInfo)

def test_metadata_url():
    aws = AWSVendorInfo()
    url = aws.metadata_url('instance-id')
    assert url == 'http://169.254.169.254/2008-02-01/meta-data/instance-id'

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_fetch(mock_open):
    mock_response = MockResponse('200', 'blah')
    mock_open.return_value = mock_response

    aws = AWSVendorInfo()
    resp = aws.fetch('foo')
    assert resp == 'blah'

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_instance_id(mock_open):
    mock_response = MockResponse('200', 'i-e7e85ce1')
    mock_open.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_id == 'i-e7e85ce1'
    mock_open.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-id',
            timeout=0.5)

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_instance_type(mock_open):
    mock_response = MockResponse('200', 'm3.medium')
    mock_open.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.instance_type == 'm3.medium'
    mock_open.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/instance-type',
            timeout=0.5)

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_availability_zone(mock_open):
    mock_response = MockResponse('200', 'us-west-2b')
    mock_open.return_value = mock_response

    aws = AWSVendorInfo()
    assert aws.availability_zone == 'us-west-2b'
    mock_open.assert_called_with(
            'http://169.254.169.254/2008-02-01/meta-data/placement/availability-zone',
            timeout=0.5)

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_fetch_timeout_socket_error(mock_open):
    mock_open.side_effect = socket.error

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_fetch_timeout_urllib2_urlerror(mock_open):
    mock_open.side_effect = urllib2.URLError('error msg')

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None

@mock.patch.object(urllib2.OpenerDirector, 'open')
def test_fetch_timeout_ioerror(mock_open):
    mock_open.side_effect = IOError

    aws = AWSVendorInfo()
    resp = aws.fetch('instance-id')
    assert resp == None


