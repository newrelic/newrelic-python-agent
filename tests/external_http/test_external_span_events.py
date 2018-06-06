import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)

import six

if six.PY2:
    import httplib
    external_library_name = 'httplib'
else:
    import http.client as httplib
    external_library_name = 'http'


@pytest.mark.parametrize('test_external', [False, True])
def test_span_events(test_external):
    guid = 'dbb536c53b749e0b'

    _settings = {
        'span_events.enabled': True,
        'feature_flag': set(['span_events']),
    }

    expected_count = int(test_external)

    exact_intrinsics = {
        'name': 'External/www.example.com/%s/' % external_library_name,
        'type': 'Span',
        'appLocalRootId': guid,
        'sampled': True,
        'priority': 0.5,

        'category': 'external',
        'externalUri': 'www.example.com',
        'externalLibrary': external_library_name,
    }
    expected_intrinsics = ('timestamp', 'duration')

    @validate_span_events(
            count=expected_count,
            exact_intrinsics=exact_intrinsics,
            expected_intrinsics=expected_intrinsics)
    @override_application_settings(_settings)
    @background_task(name='transaction')
    def _test():
        # Force intrinsics
        txn = current_transaction()
        txn.current_node.guid = '0687e0c371ea2c4e'
        txn.guid = guid
        txn._priority = 0.5
        txn._sampled = True

        if test_external:
            connection = httplib.HTTPConnection('www.example.com', 80)
            connection.request('GET', '/')
            response = connection.getresponse()
            response.read()
            connection.close()

    _test()
