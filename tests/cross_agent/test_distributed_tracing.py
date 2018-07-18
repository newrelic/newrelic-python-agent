import json
import os
import pytest
import requests
import webtest

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import BackgroundTask

from newrelic.api.cat_header_mixin import CatHeaderMixin

from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wsgi_application
from newrelic.common.object_wrapper import transient_function_wrapper
from testing_support.validators.validate_span_events import (
    validate_span_events)
from testing_support.fixtures import (override_application_settings,
    validate_transaction_event_attributes, validate_transaction_metrics,
    validate_error_event_attributes)

from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)


old_cat_id_header = CatHeaderMixin.cat_id_key
old_cat_transaction_header = CatHeaderMixin.cat_transaction_key
old_cat_appdata_header = CatHeaderMixin.cat_appdata_key
better_cat_header = CatHeaderMixin.cat_distributed_trace_key

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'distributed_tracing'))
tests = {}


def load_dt_tests():
    path = os.path.join(JSON_DIR, 'distributed_tracing.json')
    with open(path, 'r') as fh:
        for raw_test in json.load(fh):
            tests[str(raw_test['test_name'])] = CATCAT(raw_test)
    return tests.keys()


# dummy test server for validating distributed tracing on web transactions,
# which happen to be most of the transactions in the test. it will receive
# the request, make sure extra incoming payloads are ignored, generate
# an exception if necessary, and finally generate some outbound payloads
# during its response.

class TargetWSGIApplication(object):
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    @wsgi_application()
    def __call__(self, environ, start_response):
        test = tests[environ['test_name']]
        txn = current_transaction()
        txn.set_transaction_name(test.test_name)

        # we only ever process/accept the first inbound payload per
        # transaction for distributed tracing; the others should be ignored
        for i in range(1, len(test.inbound_payloads)):
            payload = ('' if test.inbound_payloads[i] is None
                           else json.dumps(test.inbound_payloads[i]))
            result = txn.accept_distributed_trace_payload(payload)
            assert not result

        if test.run_as_background_task:
            txn.background_task = True

        if test.raises_exception:
            try:
                1 / 0
            except ZeroDivisionError:
                txn.record_exception()

        with MockExternalHTTPHResponseHeadersServer() as external:
            for payload_test in test.outbound_payloads:
                sent_payloads = self.send_and_capture_outbound_request(
                    external)
                payload_test.validate_outbound_payloads(
                    test.span_events_enabled, sent_payloads)

        start_response('200 OK', self.response_headers)
        return [self.output]

    def send_and_capture_outbound_request(self, external):
        sent_payloads = []

        def capture_outbound_payloads():
            @transient_function_wrapper('newrelic.api.transaction',
                'Transaction.create_distributed_tracing_payload')
            def _capture_payloads(wrapped, instance, args, kwargs):
                result = wrapped(*args, **kwargs)
                sent_payloads.append(result)
                return result
            return _capture_payloads

        @capture_outbound_payloads()
        def _send_outbound_request():
            resp = requests.get('http://localhost:%d' % external.port)
            assert resp.status_code == 200

            assert better_cat_header.encode() in resp.content
            assert old_cat_id_header.encode() not in resp.content
            assert old_cat_transaction_header.encode() not in resp.content

        _send_outbound_request()
        return sent_payloads


class CATCAT(object):
    _params_list = [
        'test_name', 'inbound_payloads', 'trusted_account_key',
        'span_events_enabled', 'expected_metrics', 'transport_type',
        'outbound_payloads', 'account_id', 'web_transaction',
        'major_version', 'minor_version', 'raises_exception',
        'comment', 'force_sampled_true'
    ]

    def __init__(self, raw):
        for param in self._params_list:
            setattr(self, param, raw.get(param, None))

        self.events = {}
        intr = raw['intrinsics']

        for event_type in intr['target_events']:
            self.events[event_type] = CATCAT_Event(self.test_name,
                event_type, intr['common'], intr.get(event_type, {}))

        self.outbound_payloads = [] if self.outbound_payloads is None else [
            CATCAT_Outbound(ob) for ob in self.outbound_payloads
        ]

        # missing or null inbound payloads should be translated as "None"
        # in order for the test to generate the expected supportability metrics
        if not self.inbound_payloads:
            self.inbound_payloads = [None]

        # this only represents whether the test is run as a background task,
        # not whether it is supposed to be checked as a background task.
        self.run_as_background_task = (
            not(bool(self.web_transaction)) or (self.transport_type != 'HTTP'))

    def __repr__(self):
        return self.test_name + '_test'

    #############################################

    def do_background_test(self):
        with BackgroundTask(application(), name=self.test_name) as txn:
            if self.web_transaction:
                txn.background_task = False

            for p in self.inbound_payloads:
                txn.accept_distributed_trace_payload(p, self.transport_type)

    def do_http_test(self, test_app):
        payload = ('' if self.inbound_payloads[0] is None
                       else json.dumps(self.inbound_payloads[0]))
        headers = {better_cat_header: payload}
        response = test_app.get('/', headers=headers, extra_environ={
            'test_name': str(self.test_name)})
        assert old_cat_appdata_header not in response.headers


# there's 3 categories of fields to check on event attributes, which will be
# derived from the inbound payload:
#     expected, which simply need to be present in the intrinsics,
#     unexpected, which should not be present in the intrinsics,
#     exact, which require the corresponding intrinsic to have a specific value
class CATCAT_Event(object):
    def __init__(self, test_name, event_type, common, raw_event):
        self.test_name = test_name
        self.event_type = event_type

        self.exact = common.get('exact', {}).copy()
        self.exact.update(raw_event.get('exact', {}))

        self.expected = set(common.get('expected', []) +
                raw_event.get('expected', []))

        self.unexpected = set(common.get('unexpected', []) +
                raw_event.get('unexpected', []))


# similar to the inbound payloads, there's 3 categories of fields to check:
#     expected, which simply need to be present in the intrinsics,
#     unexpected, which should not be present in the intrinsics,
#     exact, which require the corresponding intrinsic to have a specific value

class CATCAT_Outbound(object):

    # we'll need to do some pre-processing here because the outbound
    # payloads have an awkward format in the .json. the "v" field is
    # specified by itself, while the "d" fields are specified as
    # "d.field", e.g. "d.id", "d.tx", etc
    def __init__(self, raw):
        self.expected = [x[2:] for x in raw.get('expected', [])]
        self.unexpected = [x[2:] for x in raw.get('unexpected', [])]

        self.expected_version = raw['exact'].pop('v')
        self.exact = {}
        for key in raw['exact']:
            self.exact[key[2:]] = raw['exact'][key]

    def validate_outbound_payloads(self, span_events_enabled, sent_payloads):

        assert sent_payloads
        payload = sent_payloads.pop()

        assert payload['v'][0] == self.expected_version[0]
        assert payload['v'][1] == self.expected_version[1]

        for key in self.exact:
            assert payload['d'][key] == self.exact[key], (key, payload)

        for key in self.expected:
            assert key in payload['d'], (key, payload)

        for key in self.unexpected:
            assert key not in payload['d'], (key, payload)


test_app = webtest.TestApp(TargetWSGIApplication())


@pytest.mark.parametrize('test_name', load_dt_tests())
def test_distributed_tracing(test_name):
    test = tests[test_name]

    def format_params(params):
        return {'agent': {}, 'user': {}, 'intrinsic': params}

    test_event = test.events['Transaction']

    @validate_transaction_event_attributes(
        exact_attrs=format_params(test_event.exact),
        required_params=format_params(test_event.expected),
        forgone_params=format_params(test_event.unexpected))
    @validate_transaction_metrics(
        test.test_name,
        rollup_metrics=test.expected_metrics,
        background_task=not(test.web_transaction)
    )
    @override_application_settings({
        'cross_application_tracer.enabled': True,
        'distributed_tracing.enabled': True,
        'span_events.enabled': test.span_events_enabled,
        'trusted_account_key': test.trusted_account_key,
        'account_id': test.account_id
    })
    def _validate_test():
        if not test.run_as_background_task:
            test.do_http_test(test_app)
        else:
            test.do_background_test()

    if 'TransactionError' in test.events:
        test_event = test.events['TransactionError']

        wrapper = validate_error_event_attributes(
            required_params=format_params(test_event.expected),
            forgone_params=format_params(test_event.unexpected),
            exact_attrs=format_params(test_event.exact))
        _validate_test = wrapper(_validate_test)

    if 'Span' in test.events:
        test_event = test.events['Span']

        wrapper = validate_span_events(
            expected_intrinsics=test_event.expected,
            unexpected_intrinsics=test_event.unexpected,
            exact_intrinsics=test_event.exact)
        _validate_test = wrapper(_validate_test)

    _validate_test()
