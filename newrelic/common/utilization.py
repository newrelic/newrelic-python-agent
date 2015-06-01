import urllib2


class AWSVendorInfo(object):

    # Use the EC2 metadata API to gather instance data.

    METADATA_HOST = '169.254.169.254'
    API_VERSION = '2008-02-01'
    TIMEOUT = 0.5

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

        url = self.metadata_url(path)
        proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)

        try:
            resp = opener.open(url, timeout=self.timeout)
        except Exception:
            self.check_metadata = False
            return None

        content = resp.read()
        return content.encode('utf-8')
