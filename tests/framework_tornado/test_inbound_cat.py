# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import pytest
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
@validate_transaction_event_attributes(
    required_params={
        'agent': (), 'user': (), 'intrinsic': (),
    },
    forgone_params={
        'agent': (), 'user': (), 'intrinsic': (),
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


@validate_transaction_event_attributes(
    required_params={'agent': (), 'user': (), 'intrinsic': ()},
    forgone_params={
        'agent': ('response.headers',),
        'user': (),
        'intrinsic': (),
    },
    exact_attrs={
        'agent': {
            'request.method': 'GET',
            'response.status': '304'},
        'user': {},
        'intrinsic': {},
    },
)
@override_application_settings(_custom_settings)
def test_cat_headers_not_inserted(app):
    payload = (
        u'1#1', u'WebTransaction/Function/app:beep',
        0, 1.23, -1,
        'dd4a810b7cb7f937', False
    )
    headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')

    client_cross_process_id = headers['X-NewRelic-ID']
    txn_header = headers['X-NewRelic-Transaction']

    response = app.fetch('/304-cat-response/%s/%s' %
            (client_cross_process_id, txn_header))
    assert response.code == 304
    assert 'X-NewRelic-App-Data' not in list(response.headers.keys())


@override_application_settings(_custom_settings)
@validate_transaction_metrics('_target_application:SimpleHandler.get',
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


@override_application_settings({
    'account_id': 1,
    'trusted_account_key': 1,
    'primary_application_id': 1,
    'distributed_tracing.enabled': True,
})
@validate_transaction_metrics(
    '_target_application:SimpleHandler.get',
    rollup_metrics=(
        ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
    )
)
def test_inbound_dt(app):
    PAYLOAD = {
        "v": [0, 1],
        "d": {
            "ac": 1,
            "ap": 1,
            "id": "7d3efb1b173fecfa",
            "tx": "e8b91a159289ff74",
            "pr": 1.234567,
            "sa": True,
            "ti": 1518469636035,
            "tr": "d6b4ba0c3a712ca",
            "ty": "App"
        }
    }
    headers = {'newrelic': json.dumps(PAYLOAD)}
    response = app.fetch('/simple', headers=headers)
    assert response.code == 200
