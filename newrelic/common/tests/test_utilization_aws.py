import mock
from newrelic.common.utilization_aws import AWSUtilization
from newrelic.packages import requests


_mock_response_data = b"""{
        "devpayProductCodes": null,
        "availabilityZone": "us-west-2c",
        "instanceId": "i-00ddba01e845e4875",
        "pendingTime": "2017-07-13T20:52:36Z",
        "region": "us-west-2",
        "privateIp": "172.31.3.45",
        "version": "2010-08-31",
        "architecture": "x86_64",
        "billingProducts": null,
        "kernelId": null,
        "ramdiskId": null,
        "imageId": "ami-6df1e514",
        "instanceType": "t2.nano",
        "accountId": "244932736945"}"""


def test_aws_vendor_info():
    aws = AWSUtilization()
    assert aws.VENDOR_NAME == 'aws'


@mock.patch.object(requests.Session, 'get')
def test_aws_good_response(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    response._content = _mock_response_data
    mock_get.return_value = response

    assert AWSUtilization.detect() == {'instanceId': 'i-00ddba01e845e4875',
            'availabilityZone': u'us-west-2c',
            'instanceType': u't2.nano'}


@mock.patch.object(requests.Session, 'get')
def test_aws_bad_response(mock_get):
    response = requests.models.Response()
    response.status_code = 500
    mock_get.return_value = response

    assert AWSUtilization.detect() is None


@mock.patch.object(requests.Session, 'get')
def test_aws_ugly_response(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    response._content = b"wruff"
    mock_get.return_value = response

    assert AWSUtilization.detect() is None
