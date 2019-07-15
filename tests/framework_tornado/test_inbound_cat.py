from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings, validate_transaction_event_attributes,
        validate_transaction_metrics)

ENCODING_KEY = '1234567890123456789012345678901234567890'


_custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': True,
        'distributed_tracing.enabled': False,
        'transaction_tracer.transaction_threshold': 0.0,
}


@override_application_settings(_custom_settings)
@validate_transaction_metrics('tornado.routing:_RoutingDelegate',
        rollup_metrics=[('ClientApplication/1#1/all', 1)])
@validate_transaction_event_attributes(
    required_params={'agent': [], 'user': [], 'intrinsic': []},
    forgone_params={'agent': [], 'user': [], 'intrinsic': []},
    exact_attrs={'agent': {}, 'user': {},
        'intrinsic': {'nr.referringTransactionGuid': 'b854df4feb2b1f06'}},
)
def test_inbound_cat_metrics_and_intrinsics(app):
    payload = ['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be']
    headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')

    response = app.fetch('/simple', headers=headers)
    assert response.code == 200
