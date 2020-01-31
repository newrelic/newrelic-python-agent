import json
import time
import unittest
import pytest

import newrelic.api.settings

from newrelic.api.application import application_instance
from newrelic.api.transaction import (current_transaction,
        accept_distributed_trace_payload, create_distributed_trace_payload)
from newrelic.api.web_transaction import WSGIWebTransaction
from newrelic.core.config import finalize_application_settings
from newrelic.core.adaptive_sampler import AdaptiveSampler
from newrelic.core.trace_cache import trace_cache

import newrelic.tests.test_cases

settings = newrelic.api.settings.settings()
application = application_instance()

OUTBOUND_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'tr', 'pr', 'sa', 'ti')


class MockApplication(object):
    def __init__(self, name='Python Application'):
        self.global_settings = finalize_application_settings()
        self.global_settings.enabled = True
        self.settings = finalize_application_settings({})
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        return None

    def compute_sampled(self):
        return False


class TestTransactionApis(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        super(TestTransactionApis, self).setUp()
        environ = {'REQUEST_URI': '/transaction_apis'}
        self.transaction = WSGIWebTransaction(application, environ)
        self.transaction._settings.distributed_tracing.enabled = True
        self.transaction._settings.span_events.enabled = True
        self.transaction._settings.collect_span_events = True

        self.application.adaptive_sampler = AdaptiveSampler(10, 60.0)

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def force_sampled(self, sampled):
        if sampled:
            # Force the adaptive sampler to reset to 0 computed calls so that
            # sampled is forced to True
            self.application.adaptive_sampler._reset()
            self.application.adaptive_sampler._reset()
        else:
            # Force sampled = False
            adaptive_sampler = self.application.adaptive_sampler
            adaptive_sampler.sampled_count = adaptive_sampler.max_sampled

    standard_test_payload = {
        'v': [0, 1],
        'd': {
            'ty': 'Mobile',
            'ac': '1',
            'tk': '1',
            'ap': '2827902',
            'pa': '5e5733a911cfbc73',
            'id': '7d3efb1b173fecfa',
            'tr': 'd6b4ba0c3a712ca',
            'ti': 1518469636035,
            'tx': '8703ff3d88eefe9d',
        }
    }

    def _make_test_payload(self, v=None, **custom_fields):
        payload = TestTransactionApis.standard_test_payload.copy()
        payload['d'] = payload['d'].copy()

        if v is not None:
            payload['v'] = v

        for field_name in custom_fields:
            payload['d'][field_name] = custom_fields[field_name]

        return payload

    ################################

    def test_create_distributed_trace_payload_text(self):
        with self.transaction:
            with pytest.warns(DeprecationWarning):
                payload = self.transaction.create_distributed_trace_payload()
            assert type(payload.text()) is str
            assert ('Supportability/DistributedTrace/'
                    'CreatePayload/Success'
                    in self.transaction._transaction_metrics)

            assert self.transaction.is_distributed_trace is True

    def test_create_distributed_trace_payload_http_safe(self):
        with self.transaction:
            with pytest.warns(DeprecationWarning):
                payload = self.transaction.create_distributed_trace_payload()
            assert type(payload.http_safe()) is str

    @pytest.mark.filterwarnings("error")
    def test_insert_distributed_trace_headers(self):
        with self.transaction:
            headers = []
            self.transaction.insert_distributed_trace_headers(headers)
            assert len(headers) == 3
            headers = dict(headers)
            assert 'traceparent' in headers
            assert 'tracestate' in headers
            assert 'newrelic' in headers
            for header in headers.values():
                assert type(header) is str

    def test_insert_distributed_trace_headers_newrelic_format_disabled(self):
        with self.transaction:
            self.transaction.settings \
                    .distributed_tracing.exclude_newrelic_header = True
            headers = []
            self.transaction.insert_distributed_trace_headers(headers)
            assert len(headers) == 2
            headers = dict(headers)
            # Assert only tracecontext headers are added
            assert 'traceparent' in headers
            assert 'tracestate' in headers
            for header in headers.values():
                assert type(header) is str

    @pytest.mark.filterwarnings("error")
    def test_accept_distributed_trace_headers(self):
        with self.transaction:
            # the tk is hardcoded in this encoded payload, so lets hardcode it
            # here, too
            self.transaction.settings.trusted_account_key = '1'

            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')

            headers = {'newrelic': payload}
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result is True

    @pytest.mark.filterwarnings("error")
    def test_accept_distributed_trace_headers_iterable(self):
        with self.transaction:
            # the tk is hardcoded in this encoded payload, so lets hardcode it
            # here, too
            self.transaction.settings.trusted_account_key = '1'

            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')

            headers = (('newrelic', payload),)
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result is True

    @pytest.mark.filterwarnings("error")
    def test_accept_distributed_trace_headers_after_invalid_payload(self):
        with self.transaction:
            headers = (('newrelic', 'invalid'),)
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result is False

            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')

            headers = (('newrelic', payload),)
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result is True

    def test_accept_distributed_trace_headers_ignores_second_call(self):
        with self.transaction:
            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')

            headers = (('newrelic', payload),)
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result
            assert self.transaction._distributed_trace_state
            assert self.transaction.parent_type == 'App'

            result = self.transaction.accept_distributed_trace_payload(headers)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/Multiple'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_headers_after_create_payload(self):
        with self.transaction:
            self.transaction.insert_distributed_trace_headers([])
            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')

            headers = (('newrelic', payload),)
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/CreateBeforeAccept'
                    in self.transaction._transaction_metrics)

    def test_distributed_trace_no_referring_transaction(self):
        with self.transaction:
            payload = self.transaction.create_distributed_trace_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Check required keys
            assert all(k in data for k in OUTBOUND_TRACE_KEYS_REQUIRED)

            # Type is always App
            assert data['ty'] == 'App'

            # IDs should be the transaction GUID
            assert data['tx'] == self.transaction.guid
            assert data['tr'].startswith(self.transaction.guid)

            # Parent should be excluded
            assert 'pa' not in data

    def test_accept_distributed_trace_w3c(self):
        with self.transaction:
            self.transaction.settings.trusted_account_key = '1'
            payload = self._make_test_payload()
            payload = json.dumps(payload)
            traceparent = \
                '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
            headers = (('newrelic', payload), ('traceparent', traceparent))
            result = self.transaction.accept_distributed_trace_headers(headers)
            assert result is True

            # Expect attributes only to be parsed from traceparent if it is
            # included and no tracestate is present, even if there is a
            # newrelic header present.
            assert self.transaction.parent_type is None
            assert self.transaction.parent_account is None
            assert self.transaction.trusted_parent_span is None
            assert self.transaction.parent_tx is None
            assert self.transaction.parent_transport_type == "HTTP"
            assert self.transaction._trace_id == \
                    '0af7651916cd43dd8448eb211c80319c'
            assert self.transaction.parent_span == '00f067aa0ba902b7'

    def test_generate_distributed_trace_invalid_data(self):
        data = {'bad_data': 0}
        with self.transaction:
            headers = \
                self.transaction._generate_distributed_trace_headers(data)
            list(headers)
            assert ('Supportability/TraceContext/'
                    'Create/Exception'
                    in self.transaction._transaction_metrics)

    def test_invalid_tracestate_header(self):
        with self.transaction:
            traceparent = \
                '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
            tracestate = 1
            headers = (('traceparent', traceparent), ('tracestate', tracestate))
            self.transaction.accept_distributed_trace_headers(headers)
            assert ('Supportability/TraceContext/'
                'TraceState/Parse/Exception'
                in self.transaction._transaction_metrics)

    ##############################################

    def _standard_trace_test(self, expected_tx, expected_id=None):
        self.transaction._trace_id = 'qwerty'
        self.transaction._priority = 1.0

        payload = self.transaction.create_distributed_trace_payload()
        assert payload['v'] == (0, 1)

        data = payload['d']

        # Type is always App
        assert data['ty'] == 'App'

        # Check required keys
        assert all(k in data for k in OUTBOUND_TRACE_KEYS_REQUIRED)

        assert data['tr'] == 'qwerty'
        assert data['pr'] == self.transaction._priority
        assert data['tx'] == expected_tx

        trusted_key = str(self.transaction.settings.trusted_account_key)
        if 'tk' in data:
            assert data['tk'] == trusted_key
        else:
            assert data['ac'] == trusted_key

        if expected_id is None:
            assert 'id' not in data
        else:
            assert data['id'] == expected_id

    def test_distributed_trace_no_spans(self):
        self.transaction._settings.span_events.enabled = False

        with self.transaction:
            self._standard_trace_test(self.transaction.guid)

    def test_distributed_trace_no_id_when_span_override_set(self):
        self.transaction._settings.collect_span_events = False

        with self.transaction:
            self._standard_trace_test(self.transaction.guid)

    def test_distributed_trace_with_spans_no_parent(self):
        with self.transaction:
            trace_cache().current_trace().guid = 'abcde'
            self.transaction.guid = 'this is guid'

            # ID and parent should be from the span
            self._standard_trace_test('this is guid', 'abcde')

    def test_distributed_trace_with_spans_not_enabled(self):
        self.transaction._settings.span_events.enabled = False

        with self.transaction:
            self._standard_trace_test(self.transaction.guid)

    def test_distributed_trace_id_omitted_when_not_sampled(self):
        with self.transaction:
            self.transaction._priority = 0.0
            self.transaction._sampled = False

            payload = self.transaction.create_distributed_trace_payload()

            data = payload['d']
            assert 'id' not in data

    ##############################################

    def test_accept_distributed_trace_payload_encoded(self):
        with self.transaction:
            # the tk is hardcoded in this encoded payload, so lets hardcode it
            # here, too
            self.transaction.settings.trusted_account_key = '1'

            payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
                'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
                'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
                'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
                'iBbMCwgMV19')
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_json(self):
        with self.transaction:
            payload = self._make_test_payload()
            payload = json.dumps(payload)
            assert isinstance(payload, str)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Success'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_discard_version(self):
        with self.transaction:
            payload = self._make_test_payload(v=[999, 0])
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/MajorVersion'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_ignore_version(self):
        with self.transaction:
            payload = self._make_test_payload(
                v=[0, 999], new_item='this field should not matter')

            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_ignores_second_call(self):
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction._distributed_trace_state
            assert self.transaction.parent_type == 'Mobile'

            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert self.transaction._distributed_trace_state
            assert self.transaction.parent_type == 'Mobile'
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/Multiple'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_discard_accounts(self):
        with self.transaction:
            payload = self._make_test_payload(ac='9999999999999')
            del payload['d']['tk']

            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/UntrustedAccount'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_tk_defaults_to_ac(self):
        with self.transaction:
            payload = self._make_test_payload()
            del payload['d']['tk']

            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_priority_found(self):
        with self.transaction:
            priority = 0.123456789
            payload = self._make_test_payload(pr=priority)

            original_priority = self.transaction.priority
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority != original_priority
            assert self.transaction.priority == priority

    def test_accept_distributed_trace_payload_id_missing(self):
        with self.transaction:
            payload = self._make_test_payload()
            del payload['d']['id']

            payload = json.dumps(payload)
            assert isinstance(payload, str)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_tx_missing(self):
        with self.transaction:
            payload = self._make_test_payload()
            del payload['d']['tx']

            payload = json.dumps(payload)
            assert isinstance(payload, str)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_id_and_tx_missing(self):
        with self.transaction:
            payload = self._make_test_payload()
            del payload['d']['id']
            del payload['d']['tx']

            payload = json.dumps(payload)
            assert isinstance(payload, str)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)

            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/ParseException'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_priority_not_found(self):
        with self.transaction:
            payload = self._make_test_payload()
            original_priority = self.transaction.priority
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority == original_priority

    def test_accept_distributed_trace_payload_sampled_not_found(self):
        with self.transaction:
            payload = self._make_test_payload()
            original_sampled = self.transaction.sampled
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.sampled == original_sampled

    def test_accept_distributed_trace_payload_trace_id(self):
        with self.transaction:
            trace_id = 'qwerty'
            payload = self._make_test_payload(tr=trace_id)

            assert self.transaction.trace_id != trace_id
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.trace_id == trace_id

    def test_accept_distributed_trace_payload_after_create_payload(self):
        with self.transaction:
            payload = self._make_test_payload()
            self.transaction.create_distributed_trace_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/CreateBeforeAccept'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_transport_duration(self):
        # Mark a payload as sent 1 second ago
        ti = int(time.time() * 1000.0) - 1000
        with self.transaction:
            payload = self._make_test_payload(ti=ti)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

            # Transport duration is at least 1 second
            assert self.transaction.parent_transport_duration > 1

    def test_accept_distributed_trace_payload_negative_duration(self):
        # Mark a payload as sent 10 seconds into the future
        ti = int(time.time() * 1000.0) + 10000
        with self.transaction:
            payload = self._make_test_payload(ti=ti)
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

            # Transport duration is 0!
            assert self.transaction.parent_transport_duration == 0

    def test_accept_distributed_trace_payload_transport_type(self):
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload,
                        transport_type='HTTPS')
            assert result
            assert self.transaction.parent_transport_type == 'HTTPS'

    def test_accept_distributed_trace_payload_unknown_transport_type(self):
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload,
                        transport_type='Kefka')
            assert result
            assert self.transaction.parent_transport_type == 'Unknown'

    def test_distributed_trace_attributes_default(self):
        with self.transaction:
            assert self.transaction.priority is None
            assert self.transaction.parent_type is None
            assert self.transaction.parent_span is None
            assert self.transaction.parent_app is None
            assert self.transaction.parent_account is None
            assert self.transaction.parent_transport_type is None
            assert self.transaction.parent_transport_duration is None
            assert self.transaction.trace_id.startswith(self.transaction.guid)
            assert self.transaction._sampled is None
            assert self.transaction._distributed_trace_state == 0
            assert self.transaction.is_distributed_trace is False

    def test_create_payload_prior_to_connect(self):
        self.transaction.enabled = False
        with self.transaction:
            assert not self.transaction.create_distributed_trace_payload()

    def test_create_payload_cat_disabled(self):
        self.transaction._settings.cross_application_tracer.enabled = False
        with self.transaction:
            assert self.transaction.create_distributed_trace_payload()

    def test_create_payload_dt_disabled(self):
        self.transaction._settings.distributed_tracing.enabled = False
        with self.transaction:
            assert not self.transaction.create_distributed_trace_payload()

    def test_accept_payload_prior_to_connect(self):
        self.transaction.enabled = False
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_payload_cat_disabled(self):
        self.transaction._settings.cross_application_tracer.enabled = False
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_payload_feature_off(self):
        self.transaction._settings.distributed_tracing.enabled = False
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_empty_payload(self):
        with self.transaction:
            payload = {}
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert len(self.transaction._transaction_metrics) == 1
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/Null'
                    in self.transaction._transaction_metrics)

    def test_accept_malformed_payload(self):
        with self.transaction:
            assert len(self.transaction._transaction_metrics) == 0
            payload = '{'
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert len(self.transaction._transaction_metrics) == 1
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/ParseException'
                    in self.transaction._transaction_metrics)

    def test_accept_version_missing(self):
        with self.transaction:
            payload = {
                'cookies': 'om nom nom',
            }
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_create_after_accept_correct_payload(self):
        with self.transaction:
            inbound_payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = self.transaction.accept_distributed_trace_payload(
                    inbound_payload)

            assert result
            outbound_payload = \
                    self.transaction.create_distributed_trace_payload()
            data = outbound_payload['d']
            assert data['ty'] == 'App'
            assert data['tr'] == 'd6b4ba0c3a712ca'

    def test_sampled_create_payload(self):
        with self.transaction:
            self.transaction._priority = 1.0
            payload = self.transaction.create_distributed_trace_payload()

            assert payload['d']['sa'] is True
            assert self.transaction.sampled is True

            assert payload['d']['pr'] == 2.0
            assert self.transaction.priority == 2.0

    def test_sampled_accept_payload(self):
        payload = self._make_test_payload(sa=True, pr=1.8)

        with self.transaction:
            with pytest.warns(DeprecationWarning):
                self.transaction.accept_distributed_trace_payload(payload)

            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.8

    def test_sampled_true_and_priority_missing(self):
        payload = self._make_test_payload(sa=True)

        with self.transaction:
            with pytest.warns(DeprecationWarning):
                self.transaction.accept_distributed_trace_payload(payload)

            # If priority is missing, sampled should not be set
            assert self.transaction.sampled is None

            # Priority should not be set if missing
            assert self.transaction.priority is None

    def test_priority_but_sampled_missing(self):
        payload = self._make_test_payload(pr=0.8)

        with self.transaction:
            with pytest.warns(DeprecationWarning):
                self.transaction.accept_distributed_trace_payload(payload)

            # Sampled remains uncomputed
            assert self.transaction.sampled is None

            # Priority should be set to payload priority
            assert self.transaction.priority == 0.8

    def test_invalid_priority(self):
        payload = self._make_test_payload(pr='WRONG')

        with self.transaction:
            assert self.transaction.accept_distributed_trace_payload(payload)

            # If invalid (non-numerical) priority, it should be set to None
            assert self.transaction.priority is None

    def test_missing_timestamp(self):
        payload = self._make_test_payload(ti=None)

        with self.transaction as txn:
            assert txn.accept_distributed_trace_payload(payload) is False

    def test_invalid_timestamp(self):
        payload = self._make_test_payload(ti='bad_timestamp')

        with self.transaction as txn:
            assert txn.accept_distributed_trace_payload(payload) is False

    def test_empty_timestamp(self):
        payload = self._make_test_payload(ti='')

        with self.transaction as txn:
            assert txn.accept_distributed_trace_payload(payload) is False

    def test_sampled_becomes_true(self):
        with self.transaction:
            self.transaction._priority = 0.0
            self.force_sampled(True)

            self.transaction._compute_sampled_and_priority()
            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.0
            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.0

    def test_sampled_becomes_false(self):
        with self.transaction:
            self.transaction._priority = 1.0
            self.force_sampled(False)

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0
            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0

    def test_compute_sampled_true_multiple_calls(self):
        with self.transaction:
            self.transaction._priority = 0.0
            self.force_sampled(True)

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.0

    def test_compute_sampled_false_multiple_calls(self):
        with self.transaction:
            self.transaction._priority = 1.0
            self.force_sampled(False)

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0

    def test_top_level_accept_api_no_transaction(self):
        payload = self._make_test_payload()
        result = accept_distributed_trace_payload(payload)
        assert result is False

    def test_top_level_accept_api_with_transaction(self):
        with self.transaction:
            payload = self._make_test_payload()
            with pytest.warns(DeprecationWarning):
                result = accept_distributed_trace_payload(payload)
            assert result is not None

    def test_top_level_create_api_no_transaction(self):
        result = create_distributed_trace_payload()
        assert result is None

    def test_top_level_create_api_with_transaction(self):
        with self.transaction:
            result = create_distributed_trace_payload()
            assert result is not None

    def test_add_agent_attributes(self):
        with self.transaction as transaction:
            transaction._add_agent_attribute('mykey', 'value')
            attributes = transaction.agent_attributes

            value = None
            for attribute in attributes:
                if attribute.name == 'mykey':
                    value = attribute.value
                    break
            assert value == 'value'


class TestTransactionDeterministic(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        environ = {'REQUEST_URI': '/transaction_apis'}
        mock_app = MockApplication()

        self.transaction = WSGIWebTransaction(mock_app, environ)
        self.transaction._settings.cross_application_tracer.enabled = True
        self.transaction._settings.distributed_tracing.enabled = True

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_sampling_probability_returns_None(self):
        with self.transaction:
            self.transaction._priority = 1.0
            self.transaction._compute_sampled_and_priority()
            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0

    def test_priority_length(self):
        with self.transaction:
            # ensure that pre-set priorities don't get truncated
            self.transaction._sampled = False
            self.transaction._priority = 0.5324235423523523
            self.transaction._compute_sampled_and_priority()
            assert self.transaction.priority == 0.5324235423523523

            # newly generated priorities should be truncated to
            # at most 5 digits behind the decimal
            self.transaction._priority = None
            self.transaction._compute_sampled_and_priority()
            assert len(str(self.transaction.priority)) <= 7


class TestTransactionComputation(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        super(TestTransactionComputation, self).setUp()

        environ = {'REQUEST_URI': '/transaction_computation'}
        self.transaction = WSGIWebTransaction(application, environ)
        self.transaction._settings.distributed_tracing.enabled = True

    def test_sampled_is_always_computed(self):
        with self.transaction:
            pass

        assert self.transaction.sampled is not None
        assert self.transaction.priority is not None


if __name__ == '__main__':
    unittest.main()
