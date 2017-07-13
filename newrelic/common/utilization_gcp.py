
from newrelic.common.utilization_common import CommonUtilization


class GCPUtilization(CommonUtilization):
    EXPECTED_KEYS = ('id', 'machineType', 'name', 'zone')
    HEADERS = {'Metadata-Flavor': 'Google'}
    METADATA_URL = 'http://%s/computeMetadata/v1/instance/?recursive=true' % (
            'metadata.google.internal')
    VENDOR_NAME = 'gcp'

    @staticmethod
    def normalize(key, data):
        if key in ('machineType', 'zone'):
            formatted = data.strip().split('/')[-1]
        elif key == 'id':
            formatted = str(data)
        else:
            formatted = data.strip()

        if GCPUtilization.valid_length(formatted) and \
                GCPUtilization.valid_chars(formatted):
            return formatted
