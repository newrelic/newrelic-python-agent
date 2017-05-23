import logging
import re

from newrelic.packages import requests
from newrelic.core.internal_metrics import internal_metric


_logger = logging.getLogger(__name__)

class AWSVendorInfo(object):

    # Use the EC2 metadata API to gather instance data.

    METADATA_HOST = '169.254.169.254'
    API_VERSION = '2008-02-01'

    def __init__(self, timeout=0.5):
        self.timeout = timeout
        self.skip_metadata_check = False

        self._instance_id = None
        self._instance_type = None
        self._availability_zone = None

    @property
    def instance_id(self):
        if not self._instance_id:
            self._instance_id = self.get('instance-id')
        return self._instance_id

    @property
    def instance_type(self):
        if not self._instance_type:
            self._instance_type = self.get('instance-type')
        return self._instance_type

    @property
    def availability_zone(self):
        if not self._availability_zone:
            self._availability_zone = self.get('placement/availability-zone')
        return self._availability_zone

    @property
    def has_data(self):
        return all([self.instance_id, self.instance_type,
                self.availability_zone])

    def metadata_url(self, path):
        return 'http://%s/%s/meta-data/%s' % (self.METADATA_HOST,
                self.API_VERSION, path)

    def get(self, path):
        data = self.fetch(path)
        return self.normalize(path, data)

    def fetch(self, path):
        if self.skip_metadata_check:
            return None

        # Create own requests session and disable all environment variables,
        # so that we can bypass any proxy set via env var for this request.

        session = requests.Session()
        session.trust_env = False

        url = self.metadata_url(path)

        try:
            resp = session.get(url, timeout=self.timeout)
        except Exception as e:
            self.skip_metadata_check = True
            _logger.debug('Error fetching AWS data for %r: %r', path, e)
            result = None
        else:
            result = resp.text

        return result

    def normalize(self, path, data):
        if not data:
            return None

        stripped = data.strip()

        if self.valid_length(stripped) and self.valid_chars(stripped):
            result = stripped
        else:
            internal_metric('Supportability/utilization/aws/error', 1)
            _logger.warning('Fetched invalid AWS data for "%r": %r', path, data)
            result = None

        return result

    def valid_length(self, data):
        bytes = data.encode('utf-8')
        return len(bytes) <= 255

    def valid_chars(self, data):
        regex = re.compile(r'[0-9a-zA-Z_ ./-]')
        for c in data:
            if not regex.match(c) and ord(c) < 0x80:
                return False
        return True

    def to_dict(self):
        return {
            'id': self.instance_id,
            'type': self.instance_type,
            'zone': self.availability_zone
        }

def aws_data():
    aws = AWSVendorInfo()
    if aws.has_data:
        return aws.to_dict()
    else:
        return None
