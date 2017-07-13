from newrelic.common.utilization_common import CommonUtilization


class GCPUtilization(CommonUtilization):
    EXPECTED_KEYS = ('id', 'machineType', 'name', 'zone')
    HEADERS = {'Metadata-Flavor': 'Google'}
    METADATA_URL = 'http://%s/computeMetadata/v1/instance/?recursive=true' % (
            'metadata.google.internal')
    VENDOR_NAME = 'gcp'

    @classmethod
    def normalize(cls, key, data):
        if data is None:
            return

        if key in ('machineType', 'zone'):
            formatted = data.strip().split('/')[-1]
        elif key == 'id':
            formatted = str(data)
        else:
            formatted = data

        return super(GCPUtilization, cls).normalize(key, formatted)
