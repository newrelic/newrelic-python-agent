
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


_mock_exception_data = """
        <?xml version="1.0" encoding="iso-8859-1"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
                 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
                 <head>
          <title>500 - Internal Server Error</title>
         </head>
         <body>
          <h1>500 - Internal Server Error</h1>
         </body>
        </html>"""


@mock.patch.object(requests.Session, 'get')
def test_aws_success(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    response._content = _mock_response_data
    mock_get.return_value = response

    assert AWSUtilization.detect() == {'instanceId': 'i-00ddba01e845e4875',
            'availabilityZone': u'us-west-2c',
            'instanceType': u't2.nano'}


@mock.patch.object(requests.Session, 'get')
def test_aws_failure(mock_get):
    response = requests.models.Response()
    response.status_code = 500
    response._content = _mock_exception_data
    mock_get.return_value = response

    assert AWSUtilization.detect() is None
