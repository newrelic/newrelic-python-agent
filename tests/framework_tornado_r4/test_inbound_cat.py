import pytest
from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings, validate_transaction_event_attributes)

ENCODING_KEY = '1234567890123456789012345678901234567890'


_custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': True,
        'transaction_tracer.transaction_threshold': 0.0,
}


@override_application_settings(_custom_settings)
@validate_transaction_event_attributes(
    required_params={
        'agent': [], 'user': [], 'intrinsic': [],
    },
    forgone_params={
        'agent': [], 'user': [], 'intrinsic': [],
    },
    exact_attrs={
        'agent': {
            'response.status': '200',
            'response.headers.contentType': 'text/html; charset=UTF-8',
        },
        'user': {}, 'intrinsic': {},
    },
)
@pytest.mark.parametrize('manual_flush', ['flush', 'no-flush'])
def test_response_to_inbound_cat(app, manual_flush):
    payload = (
        u'1#1', u'WebTransaction/Function/app:beep',
        0, 1.23, -1,
        'dd4a810b7cb7f937', False
    )
    headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')

    client_cross_process_id = headers['X-NewRelic-ID']
    txn_header = headers['X-NewRelic-Transaction']

    response = app.fetch('/force-cat-response/%s/%s/%s' %
            (client_cross_process_id, txn_header, manual_flush))
    assert response.code == 200
    assert 'X-NewRelic-App-Data' in list(response.headers.keys())
