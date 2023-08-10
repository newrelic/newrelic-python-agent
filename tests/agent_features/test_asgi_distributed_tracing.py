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
import copy

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.transaction import current_transaction
from newrelic.api.asgi_application import asgi_application, ASGIWebTransaction

from testing_support.asgi_testing import AsgiTest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


distributed_trace_intrinsics = ['guid', 'traceId', 'priority', 'sampled']
inbound_payload_intrinsics = ['parent.type', 'parent.app', 'parent.account',
        'parent.transportType', 'parent.transportDuration']

payload = {
    'v': [0, 1],
    'd': {
        'ac': '1',
        'ap': '2827902',
        'id': '7d3efb1b173fecfa',
        'pa': '5e5733a911cfbc73',
        'pr': 10.001,
        'sa': True,
        'ti': 1518469636035,
        'tr': 'd6b4ba0c3a712ca',
        'ty': 'App',
    }
}
parent_order = ['parent_type', 'parent_account',
                'parent_app', 'parent_transport_type']
parent_info = {
    'parent_type': payload['d']['ty'],
    'parent_account': payload['d']['ac'],
    'parent_app': payload['d']['ap'],
    'parent_transport_type': 'HTTP'
}


@asgi_application()
async def target_asgi_application(scope, receive, send):
    status = '200 OK'
    type = "http.response.start"
    output = b'hello world'
    response_headers = [(b'content-type', b'text/html; charset=utf-8'),
     (b'content-length', str(len(output)).encode('utf-8'))]

    txn = current_transaction()

    # Make assertions on the ASGIWebTransaction object
    assert txn._distributed_trace_state
    assert txn.parent_type == 'App'
    assert txn.parent_app == '2827902'
    assert txn.parent_account == '1'
    assert txn.parent_span == '7d3efb1b173fecfa'
    assert txn.parent_transport_type == 'HTTP'
    assert isinstance(txn.parent_transport_duration, float)
    assert txn._trace_id == 'd6b4ba0c3a712ca'
    assert txn.priority == 10.001
    assert txn.sampled

    await send({
        "type": type,
        "status": status,
        "headers": response_headers,
    })

    await send({
        "type": "http.response.body",
        "body": b"Hello World",
    })

    return [output]


test_application = AsgiTest(target_asgi_application)


_override_settings = {
    'trusted_account_key': '1',
    'distributed_tracing.enabled': True,
}

_metrics = [
        ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
        ('Supportability/TraceContext/Accept/Success', None)
]


@override_application_settings(_override_settings)
@validate_transaction_metrics(
    '',
    group='Uri',
    rollup_metrics=_metrics)
def test_distributed_tracing_web_transaction():
    headers = {'newrelic': json.dumps(payload)}
    response = test_application.make_request('GET', '/', headers=headers)
    assert 'X-NewRelic-App-Data' not in response.headers


class TestAsgiRequest(object):
    scope = {
        'asgi': {'spec_version': '2.1', 'version': '3.0'},
        'client': ('127.0.0.1', 54768),
        'headers': [(b'host', b'localhost:8000')],
        'http_version': '1.1',
        'method': 'GET',
        'path': '/',
        'query_string': b'',
        'raw_path': b'/',
        'root_path': '',
        'scheme': 'http',
        'server': ('127.0.0.1', 8000),
        'type': 'http'
    }

    async def receive(self):
        pass

    async def send(self, event):
        pass


# test our distributed_trace metrics by creating a transaction and then forcing
# it to process a distributed trace payload
@pytest.mark.parametrize('web_transaction', (True, False))
@pytest.mark.parametrize('gen_error', (True, False))
@pytest.mark.parametrize('has_parent', (True, False))
def test_distributed_tracing_metrics(web_transaction, gen_error, has_parent):
    def _make_dt_tag(pi):
        return "%s/%s/%s/%s/all" % tuple(pi[x] for x in parent_order)

    # figure out which metrics we'll see based on the test params
    # note: we'll always see DurationByCaller if the distributed
    # tracing flag is turned on
    metrics = ['DurationByCaller']
    if gen_error:
        metrics.append('ErrorsByCaller')
    if has_parent:
        metrics.append('TransportDuration')

    tag = None
    dt_payload = copy.deepcopy(payload)

    # if has_parent is True, our metric name will be info about the parent,
    # otherwise it is Unknown/Unknown/Unknown/Unknown
    if has_parent:
        tag = _make_dt_tag(parent_info)
    else:
        tag = _make_dt_tag(dict((x, 'Unknown') for x in parent_info.keys()))
        del dt_payload['d']['tr']

    # now run the test
    transaction_name = "test_dt_metrics_%s" % '_'.join(metrics)
    _rollup_metrics = [
        ("%s/%s%s" % (x, tag, bt), 1)
        for x in metrics
        for bt in ['', 'Web' if web_transaction else 'Other']
    ]

    def _make_test_transaction():
        application = application_instance()
        request = TestAsgiRequest()

        if not web_transaction:
            return BackgroundTask(application, transaction_name)

        tn = ASGIWebTransaction(application, request.scope,
                                request.send, request.receive)
        tn.set_transaction_name(transaction_name)
        return tn

    @override_application_settings(_override_settings)
    @validate_transaction_metrics(
        transaction_name,
        background_task=not(web_transaction),
        rollup_metrics=_rollup_metrics)
    def _test():
        with _make_test_transaction() as transaction:
            transaction.accept_distributed_trace_payload(dt_payload)

            if gen_error:
                try:
                    1 / 0
                except ZeroDivisionError:
                    transaction.notice_error()

    _test()
