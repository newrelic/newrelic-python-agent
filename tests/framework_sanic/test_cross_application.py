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
import re
import random
import string

from newrelic.common.encoding_utils import deobfuscate
from newrelic.api.application import application_instance
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import Transaction

from testing_support.fixtures import (override_application_settings,
        make_cross_agent_headers, validate_analytics_catmap_data,
        validate_transaction_metrics, validate_transaction_event_attributes)


BASE_METRICS = [
    ('Function/_target_application:index', 1),
]
DT_METRICS = [
    ('Supportability/DistributedTrace/AcceptPayload/Success', None),
    ('Supportability/TraceContext/TraceParent/Accept/Success', 1),
]
BASE_ATTRS = ['response.status', 'response.headers.contentType',
        'response.headers.contentLength']


@validate_transaction_metrics(
    '_target_application:index',
    scoped_metrics=BASE_METRICS,
    rollup_metrics=BASE_METRICS + DT_METRICS,
)
@override_application_settings({
    'distributed_tracing.enabled': True,
})
@validate_transaction_event_attributes(
    required_params={'agent': BASE_ATTRS, 'user': [], 'intrinsic': []},
)
def test_inbound_distributed_trace(app):
    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    response = app.fetch('get', '/', headers=dict(dt_headers))
    assert response.status == 200


ENCODING_KEY = "".join(random.choice(string.ascii_lowercase) for _ in range(40))
_cat_response_header_urls_to_test = (
        ('/', '_target_application:index'),
        ('/streaming', '_target_application:streaming'),
        ('/error', '_target_application:error'),
)
_custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': True,
        'distributed_tracing.enabled': False,
}


def _get_cat_response_header(raw_response):
    match = re.search(r'X-NewRelic-App-Data: (.*)\r',
            raw_response.decode('utf-8'))
    if match:
        return match.group(1).strip()


@pytest.mark.parametrize(
    'inbound_payload,expected_intrinsics,forgone_intrinsics,cat_id', [

    # Valid payload from trusted account
    (['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be'],
    {'nr.referringTransactionGuid': 'b854df4feb2b1f06',
    'nr.tripId': '7e249074f277923d',
    'nr.referringPathHash': '5d2957be'},
    [],
    '1#1'),

    # Valid payload from an untrusted account
    (['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be'],
    {},
    ['nr.referringTransactionGuid', 'nr.tripId', 'nr.referringPathHash'],
    '80#1'),
])
@pytest.mark.parametrize('url,metric_name', _cat_response_header_urls_to_test)
def test_cat_response_headers(app, inbound_payload, expected_intrinsics,
        forgone_intrinsics, cat_id, url, metric_name):

    _base_metrics = [
        ('Function/%s' % metric_name, 1),
    ]

    @validate_transaction_metrics(
        metric_name,
        scoped_metrics=_base_metrics,
        rollup_metrics=_base_metrics,
    )
    @validate_analytics_catmap_data(
            'WebTransaction/Function/%s' % metric_name,
            expected_attributes=expected_intrinsics,
            non_expected_attributes=forgone_intrinsics)
    @override_application_settings(_custom_settings)
    def _test():
        cat_headers = make_cross_agent_headers(inbound_payload, ENCODING_KEY,
                cat_id)
        response = app.fetch('get', url, headers=dict(cat_headers))

        if expected_intrinsics:
            # test valid CAT response header
            assert b'X-NewRelic-App-Data' in response.raw_headers
            cat_response_header = _get_cat_response_header(
                    response.raw_headers)

            app_data = json.loads(deobfuscate(cat_response_header,
                    ENCODING_KEY))
            assert app_data[0] == cat_id
            assert app_data[1] == ('WebTransaction/Function/%s' % metric_name)
        else:
            assert b'X-NewRelic-App-Data' not in response.raw_headers

    _test()


@override_application_settings(_custom_settings)
def test_cat_response_custom_header(app):
    inbound_payload = ['b854df4feb2b1f06', False, '7e249074f277923d',
            '5d2957be']
    cat_id = '1#1'
    custom_header_value = b'my-custom-header-value'
    cat_headers = make_cross_agent_headers(inbound_payload, ENCODING_KEY,
            cat_id)

    response = app.fetch('get', '/custom-header/%s/%s' % (
                'X-NewRelic-App-Data', custom_header_value),
            headers=dict(cat_headers))
    assert custom_header_value in response.raw_headers, response.raw_headers
