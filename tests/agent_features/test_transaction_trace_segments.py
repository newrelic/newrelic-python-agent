from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import external_trace, ExternalTrace
from newrelic.api.background_task import background_task

from testing_support.fixtures import (override_application_settings,
        validate_tt_segment_params)


@external_trace('lib', 'https://example.com/path?q=q#frag')
def external():
    pass


@validate_tt_segment_params(present_params=('http.url',))
@background_task(name='test_external_segment_attributes_default')
def test_external_segment_attributes_default():
    external()


@override_application_settings({
    'transaction_segments.attributes.exclude': ['http.url'],
})
@validate_tt_segment_params(forgone_params=('http.url',))
@background_task(name='test_external_segment_attributes_disabled')
def test_external_segment_attributes_disabled():
    external()


@validate_tt_segment_params(exact_params={'http.url': 'http://example.org'})
@background_task(name='test_external_user_params_override_url')
def test_external_user_params_override_url():
    transaction = current_transaction()
    with ExternalTrace(transaction, 'lib', 'http://example.com') as t:
        # Pretend like this is a user attribute and it's legal to do this
        t.params['http.url'] = 'http://example.org'
