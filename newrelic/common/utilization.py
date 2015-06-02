from newrelic.packages import requests


class AWSVendorInfo(object):

    # Use the EC2 metadata API to gather instance data.

    METADATA_HOST = '169.254.169.254'
    API_VERSION = '2008-02-01'
    TIMEOUT = 0.25

    def __init__(self, timeout=None):
        self.timeout = timeout or self.TIMEOUT
        self.check_metadata = True

    @property
    def instance_id(self):
        return self.fetch('instance-id')

    @property
    def instance_type(self):
        return self.fetch('instance-type')

    @property
    def availability_zone(self):
        return self.fetch('placement/availability-zone')

    def metadata_url(self, path):
        return 'http://%s/%s/meta-data/%s' % (self.METADATA_HOST,
                self.API_VERSION, path)

    def fetch(self, path):
        if not self.check_metadata:
            return None

        # Use own requests session to disable all environment variables. This
        # allows us to bypass any proxy set via env var for this request.

        session = requests.Session()
        session.trust_env = False

        url = self.metadata_url(path)

        try:
            resp = session.get(url, timeout=self.timeout)
        except Exception:
            self.check_metadata = False
            return None

        content = resp.read()
        return content
