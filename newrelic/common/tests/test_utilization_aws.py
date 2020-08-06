import pytest
import functools
import logging

from newrelic.common.utilization import AWSUtilization
from newrelic.common.tests.test_utilization_common import http_client_cls

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


def test_aws_good_response():
    AWSUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=_mock_response_data,
                                            utilization_cls=AWSUtilization)

    assert AWSUtilization.detect() == {'instanceId': 'i-00ddba01e845e4875',
            'availabilityZone': u'us-west-2c',
            'instanceType': u't2.nano'}

    assert not AWSUtilization.CLIENT_CLS.FAIL


def test_aws_error_status():
    AWSUtilization.CLIENT_CLS = http_client_cls(status=500,
                                            data=b"",
                                            utilization_cls=AWSUtilization)

    assert AWSUtilization.detect() is None


@pytest.mark.parametrize('body', (b"wruff", b""))
def test_aws_invalid_response(body):
    AWSUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=body,
                                            utilization_cls=AWSUtilization)

    assert AWSUtilization.detect() is None


def test_aws_fetch_log(caplog):
    caplog.set_level(logging.DEBUG)

    metadata_url = AWSUtilization.METADATA_HOST + AWSUtilization.METADATA_PATH

    AWSUtilization.CLIENT_CLS = http_client_cls(status=404,
                                            data=None,
                                            utilization_cls=AWSUtilization)
    AWSUtilization.fetch()

    assert len(caplog.records) == 1

    message = caplog.records[0].getMessage()

    assert metadata_url in message
