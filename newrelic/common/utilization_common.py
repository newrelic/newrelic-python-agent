import logging
import re

from newrelic.packages import requests
from newrelic.core.internal_metrics import internal_metric


_logger = logging.getLogger(__name__)
VALID_CHARS_RE = re.compile(r'[0-9a-zA-Z_ ./-]')


class CommonUtilization(object):
    METADATA_URL = ''
    HEADERS = None
    EXPECTED_KEYS = []
    VENDOR_NAME = ''
    TIMEOUT = 0.5

    @classmethod
    def record_error(cls, resource, data):
        # As per spec
        internal_metric(
                'Supportability/utilization/%s/error' % cls.VENDOR_NAME, 1)
        _logger.warning('Invalid %r data (%r): %r',
                cls.VENDOR_NAME, resource, data)

    @classmethod
    def fetch(cls):
        # Create own requests session and disable all environment variables,
        # so that we can bypass any proxy set via env var for this request.

        session = requests.Session()
        session.trust_env = False

        try:
            resp = session.get(cls.METADATA_URL, timeout=cls.TIMEOUT,
                    headers=cls.HEADERS)
            resp.raise_for_status()
        except Exception as e:
            resp = None
            _logger.debug('Error fetching %s data from %r: %r',
                    cls.VENDOR_NAME, cls.METADATA_URL, e)

        return resp

    @classmethod
    def get_values(cls, response):
        if response is None:
            return

        try:
            j = response.json()
        except ValueError:
            _logger.debug('Invalid %s data (%r): %r',
                    cls.VENDOR_NAME, cls.METADATA_URL, response.text)
            return

        return j

    @classmethod
    def valid_chars(cls, data):
        if data is None:
            return False

        for c in data:
            if not VALID_CHARS_RE.match(c) and ord(c) < 0x80:
                cls.record_error('valid_chars', data)
                return False

        return True

    @classmethod
    def valid_length(cls, data):
        if data is None:
            return False

        b = data.encode('utf-8')
        valid = len(b) <= 255
        if valid:
            return True

        cls.record_error('valid_length', data)
        return False

    @classmethod
    def normalize(cls, key, data):
        if data is None:
            return

        try:
            stripped = data.strip()

            if (stripped and cls.valid_length(stripped) and
                    cls.valid_chars(stripped)):
                return stripped
        except:
            pass

    @classmethod
    def sanitize(cls, values):
        if values is None:
            return

        out = {}
        for key in cls.EXPECTED_KEYS:
            metadata = values.get(key, None)
            if not metadata:
                cls.record_error(key, metadata)
                return

            normalized = cls.normalize(key, metadata)
            if not normalized:
                cls.record_error(key, metadata)
                return

            out[key] = normalized

        return out

    @classmethod
    def detect(cls):
        response = cls.fetch()
        values = cls.get_values(response)
        return cls.sanitize(values)
