
from newrelic.common.utilization_common import CommonUtilization


class AWSUtilization(CommonUtilization):
    EXPECTED_KEYS = ('availabilityZone', 'instanceId', 'instanceType')
    METADATA_URL = '%s/2016-09-02/dynamic/instance-identity/document' % (
        'http://169.254.169.254'
    )
    VENDOR_NAME = 'aws'
