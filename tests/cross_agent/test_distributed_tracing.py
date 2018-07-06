import itertools
import json
import os
import pytest
import requests
import six
import webtest

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import BackgroundTask

from newrelic.api.cat_header_mixin import CatHeaderMixin

from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wsgi_application
from newrelic.common.object_wrapper import transient_function_wrapper
from testing_support.fixtures import (override_application_settings,
                                      validate_transaction_metrics)

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


def assert_xnor(a, b):
    assert not (a ^ b)


def load_dt_tests():
    global tests

    path = os.path.join(JSON_DIR, 'distributed_tracing.json')
    with open(path, 'r') as fh:
        for raw_test in json.load(fh):
            tests[str(raw_test['test_name'])] = CATCAT(raw_test)

        return itertools.product(tests.keys(), (False, True), (False, True))


# dummy test server for validating distributed tracing on web transactions,
# which happen to be most of the transactions in the test. it will receive
# the request, make sure extra incoming payloads are ignored, generate
# an exception if necessary, and finally generate some outbound payloads
# during its response.

class TargetWSGIApplication(object):
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    dt_headers = {
        better_cat_header: True,
        old_cat_id_header: False,
        old_cat_transaction_header: False
    }

    @wsgi_application()
    def __call__(self, environ, start_response):
        test = tests[environ['test_name']]
        txn = current_transaction()

        self.validate_extra_inbound_requests(test, txn)
        self.process_request(test, txn)
        self.send_and_validate_outbound_requests(test, txn)

        start_response('200 OK', self.response_headers)
        return [self.output]

    # we only ever process/accept the first inbound payload per
    # transaction for distributed tracing; the others should be ignored
    def validate_extra_inbound_requests(self, test, txn):
        for i in range(1, len(test.inbound_payloads)):
            payload = test.inbound_payloads[i]
            result = txn.accept_distributed_trace_payload(payload)
            assert not result

    def process_request(self, test, txn):
        txn.set_transaction_name(test.test_name)

        if test.background_task:
            txn.background_task = True

        if test.raises_exception:
            try:
                1 / 0
            except ZeroDivisionError:
                txn.record_exception()

    def send_and_validate_outbound_requests(self, test, txn):
        with MockExternalHTTPHResponseHeadersServer() as external:
            for payload_test in test.outbound_payloads:
                sent_payloads = self.send_and_capture_outbound_request(
                    test.dt_enabled, external)

                payload_test.validate(
                    test.dt_enabled, test.spans_enabled, sent_payloads)

    def send_and_capture_outbound_request(self, dt_enabled, external):
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

            # in addition to sending, we'll also validate the headers
            # while we're here. because, well.. shucks. why the heck not?
            for header, for_dt in six.iteritems(self.dt_headers):
                assert_xnor(dt_enabled == for_dt, header in resp.content)

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

    event_type_map = {
        'Transaction': 'transaction_events',
        'TransactionError': 'error_events',
        'Span': 'span_events'
    }

    def __init__(self, raw):
        self.dt_enabled = False
        self.spans_enabled = False

        for param in self._params_list:
            setattr(self, param, raw.get(param, None))

        self.events = {}
        self.root_span_id = None
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

        # we'll need to know this for validating span parenting
        elif ('d' in self.inbound_payloads[0]) and ('id' in
                self.inbound_payloads[0]['d']):
            self.root_span_id = self.inbound_payloads[0]['d']['id']

        # this only represents whether the test is run as a background task,
        # not whether it is supposed to be checked as a background task.
        self.background_task = (not(bool(self.web_transaction)) or
                                    (self.transport_type != 'HTTP'))

    def set_settings(self, dt_enabled, spans_enabled):
        self.dt_enabled = dt_enabled
        self.spans_enabled = (
                dt_enabled and spans_enabled and self.span_events_enabled)

    def __repr__(self):
        return self.test_name + '_test'

    #############################################

    def capture_events(self):
        self.event_data = {}

        @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
        def _capture_events(wrapped, instance, args, kwargs):
            result = wrapped(*args, **kwargs)

            for event_type in self.event_type_map:
                event_attr = self.event_type_map[event_type]
                for event_data in getattr(instance, event_attr).samples:
                    (intrinsics, user_attr, agent_attr) = event_data
                    self.event_data.setdefault(event_type, [])
                    self.event_data[event_type].append(intrinsics)

            return result
        return _capture_events

    def validate(self, dt_enabled, spans_enabled, test_app):
        self.set_settings(dt_enabled, spans_enabled)
        for event in self.events.values():
            event.reset()

        @self.capture_events()
        @validate_transaction_metrics(
            self.test_name,
            rollup_metrics=self.expected_metrics if self.dt_enabled else [],
            background_task=not(self.web_transaction))
        @override_application_settings({
            'cross_application_tracer.enabled': True,
            'distributed_tracing.enabled': self.dt_enabled,
            'span_events.enabled': self.spans_enabled,
            'trusted_account_key': self.trusted_account_key,
            'account_id': self.account_id
        })
        def _validate_inbound():
            if self.web_transaction and (self.transport_type == 'HTTP'):
                self.http_test(test_app)
            else:
                self.background_test()

        _validate_inbound()
        self.validate_events()

    # we capture the events and then validate them afterwards in bulk so that
    # we can correctly track and then validate span parenting
    def validate_events(self):
        if not self.spans_enabled:
            assert 'Span' not in self.event_data

        for event_type in self.events:
            if (event_type == 'Span') and not(self.spans_enabled):
                continue

            assert event_type in self.event_data

        for event_type in self.event_data:
            for intrinsics in self.event_data[event_type]:
                assert event_type == intrinsics['type']
                self.events[event_type].validate(self.dt_enabled,
                    self.spans_enabled, self.raises_exception, intrinsics)

        if (self.spans_enabled) and ('Span' in self.events):
            self.events['Span'].validate_span_parenting(self.root_span_id)

    def background_test(self):
        with BackgroundTask(application(), name=self.test_name) as txn:
            if self.web_transaction:
                txn.background_task = False

            for p in self.inbound_payloads:
                txn.accept_distributed_trace_payload(p, self.transport_type)

    def http_test(self, test_app):
        headers = {better_cat_header: json.dumps(self.inbound_payloads[0])}
        response = test_app.get('/', headers=headers, extra_environ={
            'test_name': str(self.test_name)})
        assert old_cat_appdata_header not in response.headers


# there's 3 categories of fields to check on event attributes, which will be
# derived from the inbound payload:
#     expected, which simply need to be present in the intrinsics,
#     unexpected, which should not be present in the intrinsics,
#     exact, which require the corresponding intrinsic to have a specific value
#
# in addition, spans have a few fields that change based on a span's location
# in the span hierarchy, so we'll check them seperately.

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

        self.span_children = {}
        self.entry_span = None

        # Note: parentId will be checked explicitly by validate_span_parenting
        #       for all Span events
        self.spans_disabled_in_parent = False
        if event_type == 'Span':
            if 'parentId' in self.unexpected:
                self.spans_disabled_in_parent = True
                self.unexpected.remove('parentId')

            elif 'parentId' in self.exact:
                del self.exact['parentId']

    def reset(self):
        self.span_children = {}
        self.entry_span = None

    def validate(self, dt_enabled, spans_enabled, has_error, intrinsics):
        if not spans_enabled:
            assert 'parentSpanId' not in intrinsics

        if dt_enabled:
            self.record_span_parenting(spans_enabled, intrinsics)

            for param in self.expected:
                assert param in intrinsics, str(intrinsics)

            for param in self.unexpected:
                assert param not in intrinsics, str(intrinsics)

            for param, value in self.exact.items():
                if not(spans_enabled) and (param == 'parentSpanId'):
                    assert 'parentSpanId' not in intrinsics, (
                        (param, value), str(intrinsics))

                else:
                    assert intrinsics[param] == value, (
                        (param, value), str(intrinsics))

        else:
            for param in list(self.exact.keys()) + list(self.expected):
                # if an exception is thrown, an error attribute will always
                # be thrown
                if has_error and (param == 'error'):
                    assert 'error' in intrinsics, str(intrinsics)
                else:
                    assert param not in intrinsics, str(intrinsics)

    # record which spans are parented under which other spans so that we can
    # validate that all seen spans have a parent.

    def record_span_parenting(self, spans_enabled, intrinsics):
        if not(spans_enabled) or (self.event_type != 'Span'):
            return

        # only the root span should have 'nr.entryPoint'
        is_root_span = (intrinsics['name'] == 'Function/' + self.test_name)
        assert_xnor(is_root_span, 'nr.entryPoint' in intrinsics)

        if is_root_span:
            self.entry_span = intrinsics['guid']
            if 'parentId' in intrinsics:
                self.span_children[intrinsics['parentId']] = [self.entry_span]

        else:
            assert 'parentId' in intrinsics

            self.span_children.setdefault(intrinsics['parentId'], [])
            self.span_children[intrinsics['parentId']].append(
                intrinsics['guid'])

        # if we get an incoming payload without an 'id' field, that means
        # the agent generating this payload had span_events.enabled set to
        # False for some reason. However, our agent might have it set to
        # True, so we should be generating span events for this transaction.
        # However! the root span event of this transaction should not have
        # a parentId attribute since one wasn't there in the inbound
        # payload!

        if self.spans_disabled_in_parent:
            assert_xnor(is_root_span, 'parentId' not in intrinsics)

    # starting from the root span (either from the inbound if its present,
    # or otherwise the entry point span of this transaction), we go through
    # the span hierarchy and make sure each span we've seen is accounted for.

    def validate_span_parenting(self, incoming_parent_span_id):
        parent_queue = [incoming_parent_span_id or self.entry_span]

        while len(parent_queue) > 0:
            parent_span_id = parent_queue.pop(0)
            for span_id in self.span_children[parent_span_id]:
                if span_id in self.span_children:
                    parent_queue.append(span_id)

            del self.span_children[parent_span_id]

        assert len(self.span_children) == 0


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

    def validate(self, dt_enabled, spans_enabled, sent_payloads):
        if dt_enabled:
            assert sent_payloads
            payload = sent_payloads.pop()

            assert payload['v'][0] == self.expected_version[0]
            assert payload['v'][1] == self.expected_version[1]

            for key in self.exact:
                assert payload['d'][key] == self.exact[key], (key, payload)

            for key in self.expected:
                if not (spans_enabled) and (key == 'id'):
                    assert 'id' not in payload['d']
                else:
                    assert key in payload['d'], (key, payload)

            for key in self.unexpected:
                assert key not in payload['d'], (key, payload)

        else:
            assert not sent_payloads


test_app = webtest.TestApp(TargetWSGIApplication())


@pytest.mark.parametrize('test_name,dt_enabled,spans_enabled', load_dt_tests())
def test_distributed_tracing_inbound(test_name, dt_enabled, spans_enabled):
    tests[test_name].validate(dt_enabled, spans_enabled, test_app)
