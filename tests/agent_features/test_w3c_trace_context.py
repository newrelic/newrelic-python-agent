import json
import webtest

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.wsgi_application import wsgi_application
from testing_support.fixtures import override_application_settings


@wsgi_application()
def target_wsgi_application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])
    txn = current_transaction()
    headers = ExternalTrace.generate_request_headers(txn)
    return [json.dumps(headers).encode('utf-8')]


test_application = webtest.TestApp(target_wsgi_application)


_override_settings = {
    'trusted_account_key': '1',
    'distributed_tracing.enabled': True,
    'distributed_tracing.format': 'w3c',
}


INBOUND_TRACEPARENT = '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACESTATE = 'rojo=00f067aa0ba902b7,congo=t61rcWkgMzE'


@override_application_settings(_override_settings)
def test_tracestate_is_propagated():
    headers = {
        'traceparent': INBOUND_TRACEPARENT,
        'tracestate': INBOUND_TRACESTATE,
    }
    response = test_application.get('/', headers=headers)
    for header_name, header_value in response.json:
        if header_name == 'tracestate':
            break
    else:
        assert False, 'tracestate header not propagated'

    # Allow for NR values to be prepended to the tracestate. The tracestate
    # must still contain the unmodified inbound tracestate.
    assert header_value.endswith(INBOUND_TRACESTATE)
