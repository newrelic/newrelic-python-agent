import pytest
import sys

from tornado.ioloop import IOLoop

from testing_support.fixtures import (validate_synthetics_event,
        override_application_settings, make_synthetics_header)


ENCODING_KEY = '1234567890123456789012345678901234567890'
ACCOUNT_ID = '444'
SYNTHETICS_RESOURCE_ID = '09845779-16ef-4fa7-b7f2-44da8e62931c'
SYNTHETICS_JOB_ID = '8c7dd3ba-4933-4cbb-b1ed-b62f511782f4'
SYNTHETICS_MONITOR_ID = 'dc452ae9-1a93-4ab5-8a33-600521e9cd00'

_override_settings = {
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [int(ACCOUNT_ID)],
    'synthetics.enabled': True,
}

if (sys.version_info < (3, 4) or
        IOLoop.configurable_default().__name__ == 'AsyncIOLoop'):
    loops = [None, 'zmq.eventloop.ioloop.ZMQIOLoop']
else:
    loops = [None, 'tornado.platform.asyncio.AsyncIOLoop',
            'zmq.eventloop.ioloop.ZMQIOLoop']


def _make_synthetics_header(version='1', account_id=ACCOUNT_ID,
        resource_id=SYNTHETICS_RESOURCE_ID, job_id=SYNTHETICS_JOB_ID,
        monitor_id=SYNTHETICS_MONITOR_ID, encoding_key=ENCODING_KEY):
    return make_synthetics_header(account_id, resource_id, job_id,
            monitor_id, encoding_key, version)


_test_valid_synthetics_event_required = [
        ('nr.syntheticsResourceId', SYNTHETICS_RESOURCE_ID),
        ('nr.syntheticsJobId', SYNTHETICS_JOB_ID),
        ('nr.syntheticsMonitorId', SYNTHETICS_MONITOR_ID)]
_test_valid_synthetics_event_forgone = []


@pytest.mark.parametrize('ioloop', loops)
@override_application_settings(_override_settings)
def test_valid_synthetics_event(app, ioloop):

    @validate_synthetics_event(_test_valid_synthetics_event_required,
            _test_valid_synthetics_event_forgone, should_exist=True)
    def _test():
        headers = _make_synthetics_header()
        response = app.fetch('/simple/fast', headers=headers)
        assert response.code == 200

    _test()
