import json
import time
import unittest

import newrelic.api.settings

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.core.config import finalize_application_settings

import newrelic.tests.test_cases

settings = newrelic.api.settings.settings()
application = application_instance()


DISTRIBUTED_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'id', 'tr', 'pr', 'sa', 'ti')


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

    def compute_sampled(self, priority):
        return False


class TestTraceEndsAfterTransaction(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        environ = {'REQUEST_URI': '/trace_ends_after_txn'}
        self.transaction = WebTransaction(application, environ)

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_simple(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()

        assert not self.transaction.enabled
        assert trace_1.exited
        assert trace_2.exited

    def test_max_depth_exceeded(self):
        with self.transaction:
            self.transaction._settings.agent_limits.max_outstanding_traces = 3
            for i in range(4):
                trace = FunctionTrace(self.transaction,
                        'I am going to be little late, %s' % i)
                trace.__enter__()

        assert self.transaction.enabled

    def test_one_trace_exited_one_still_running(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')

            with trace_1:
                trace_2 = FunctionTrace(
                        self.transaction, 'I am going to be a little later')
                trace_2.__enter__()

        assert not self.transaction.enabled
        assert trace_1.exited
        assert trace_2.exited

    def test_siblings_not_completed(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()
            self.transaction._pop_current(trace_1)

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()

            assert trace_1.parent == trace_2.parent

        assert not self.transaction.enabled
        assert not trace_1.exited
        assert trace_2.exited

    def test_async_children_not_completed(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()
            self.transaction._pop_current(trace_2)

            trace_3 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_3.__enter__()
            self.transaction._pop_current(trace_3)

        assert not self.transaction.enabled
        assert trace_1.exited


class TestTransactionApis(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        super(TestTransactionApis, self).setUp()
        environ = {'REQUEST_URI': '/transaction_apis'}
        self.transaction = WebTransaction(application, environ)
        self.transaction._settings.cross_application_tracer.enabled = True
        self.transaction._settings.feature_flag = set(['distributed_tracing'])

        self.application._transaction_sampled_count = 0
        self.application._min_sampling_priority = 0.0

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_create_distributed_tracing_payload_text(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert type(payload.text()) is str
            assert ('Supportability/DistributedTrace/'
                    'CreatePayload/Success'
                    in self.transaction._transaction_metrics)

    def test_create_distributed_tracing_payload_http_safe(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert type(payload.http_safe()) is str

    def test_distributed_trace_no_referring_transaction(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Check required keys
            assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

            # Type is always App
            assert data['ty'] == 'App'

            # IDs should be the transaction GUID
            assert data['id'] == self.transaction.guid
            assert data['tr'] == self.transaction.guid

            # Parent should be excluded
            assert 'pa' not in data

    def test_distributed_trace_referring_transaction(self):
        with self.transaction:
            self.transaction.parent_id = 'abcde'
            self.transaction._trace_id = 'qwerty'
            self.transaction._priority = 1.0

            payload = self.transaction.create_distributed_tracing_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Type is always App
            assert data['ty'] == 'App'

            # Check required keys
            assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

            # ID should be the transaction GUID
            assert data['id'] == self.transaction.guid

            # Parent data should be forwarded
            assert data['pa'] == 'abcde'
            assert data['tr'] == 'qwerty'
            assert data['pr'] == self.transaction._priority

    def test_distributed_trace_with_spans_no_parent(self):
        self.transaction._settings.feature_flag.add('span_events')
        with self.transaction:
            self.transaction.current_node.guid = 'abcde'
            self.transaction.guid = 'this is guid'
            self.transaction._trace_id = 'qwerty'
            self.transaction._priority = 1.0

            payload = self.transaction.create_distributed_tracing_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Type is always App
            assert data['ty'] == 'App'

            # Check required keys
            assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

            # ID and parent should be from the span
            assert data['id'] == 'abcde'
            assert data['pa'] == 'this is guid'

            # Parent data should be forwarded
            assert data['tr'] == 'qwerty'
            assert data['pr'] == self.transaction._priority

    def test_distributed_trace_with_spans_with_parent(self):
        self.transaction._settings.feature_flag.add('span_events')
        with self.transaction:
            with FunctionTrace(self.transaction, 'trace_1') as trace:
                trace.guid = 'abcde'
                trace.parent.guid = 'this is guid'
                self.transaction._trace_id = 'qwerty'
                self.transaction._priority = 1.0

                payload = self.transaction.create_distributed_tracing_payload()
                assert payload['v'] == (0, 1)

                data = payload['d']

                # Type is always App
                assert data['ty'] == 'App'

                # Check required keys
                assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

                # ID and parent should be from the span
                assert data['id'] == 'abcde'
                assert data['pa'] == 'this is guid'

                # Parent data should be forwarded
                assert data['tr'] == 'qwerty'
                assert data['pr'] == self.transaction._priority

    def test_accept_distributed_trace_payload_encoded(self):
        with self.transaction:
            payload = ('eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkFwcCIsImFjIjoiMjAyNjQiLC'
                'JhcCI6IjEwMTk1IiwiaWQiOiIyNjFhY2E5YmM4YWVjMzc0IiwidHIiOiIyNjF'
                'hY2E5YmM4YWVjMzc0IiwicHIiOjAuMjczMTM1OTc2NTQ0MjQ1NCwic2EiOmZh'
                'bHNlLCJ0aSI6MTUyNDAxMDIyNjYxMH19')
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_json(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            payload = json.dumps(payload)
            assert isinstance(payload, str)
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Success'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_discard_version(self):
        with self.transaction:
            payload = {
                'v': [999, 0],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/MajorVersion'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_ignore_version(self):
        with self.transaction:
            payload = {
                'v': [0, 999],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                    'new_item': 'this field should not matter',
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_ignores_second_call(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.is_distributed_trace
            assert self.transaction.parent_type == 'Mobile'

            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'App',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert self.transaction.is_distributed_trace
            assert self.transaction.parent_type == 'Mobile'
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/Multiple'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_discard_accounts(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '9999999999999',  # non-trusted account
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/UntrustedAccount'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_priority_found(self):
        with self.transaction:
            priority = 0.123456789
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                    'pr': priority
                }
            }
            original_priority = self.transaction.priority
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority != original_priority
            assert self.transaction.priority == priority

    def test_accept_distributed_trace_payload_id_missing(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            payload = json.dumps(payload)
            assert isinstance(payload, str)
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/ParseException'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_priority_not_found(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            original_priority = self.transaction.priority
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority == original_priority

    def test_accept_distributed_trace_payload_sampled_not_found(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            original_sampled = self.transaction.sampled
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.sampled == original_sampled

    def test_accept_distributed_trace_payload_parent_grandparent_ids(self):
        with self.transaction:
            parent_id = 'parent id'
            grandparent_id = 'grandparent id'
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': grandparent_id,
                    'id': parent_id,
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.parent_id == parent_id
            assert self.transaction.grandparent_id == grandparent_id

    def test_accept_distributed_trace_payload_trace_id(self):
        with self.transaction:
            trace_id = 'qwerty'
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': trace_id,
                    'ti': 1518469636035,
                }
            }
            assert self.transaction.trace_id != trace_id
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.trace_id == trace_id

    def test_accept_distributed_trace_payload_after_create_payload(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            self.transaction.create_distributed_tracing_payload()
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert ('Supportability/DistributedTrace/'
                    'AcceptPayload/Ignored/CreateBeforeAccept'
                    in self.transaction._transaction_metrics)

    def test_accept_distributed_trace_payload_transport_duration(self):
        # Mark a payload as sent 1 second ago
        ti = int(time.time() * 1000.0) - 1000
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': ti,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

            # Transport duration is at least 1 second
            assert self.transaction.parent_transport_duration > 1

    def test_distributed_trace_attributes_default(self):
        with self.transaction:
            assert self.transaction.priority is None
            assert self.transaction.parent_type is None
            assert self.transaction.parent_id is None
            assert self.transaction.grandparent_id is None
            assert self.transaction.parent_app is None
            assert self.transaction.parent_account is None
            assert self.transaction.parent_transport_type is None
            assert self.transaction.parent_transport_duration is None
            assert self.transaction.trace_id == self.transaction.guid
            assert self.transaction._sampled is None
            assert self.transaction.is_distributed_trace is False

    def test_create_payload_prior_to_connect(self):
        self.transaction.enabled = False
        with self.transaction:
            assert not self.transaction.create_distributed_tracing_payload()

    def test_create_payload_cat_disabled(self):
        self.transaction._settings.cross_application_tracer.enabled = False
        with self.transaction:
            assert not self.transaction.create_distributed_tracing_payload()

    def test_accept_payload_prior_to_connect(self):
        self.transaction.enabled = False
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_payload_cat_disabled(self):
        self.transaction._settings.cross_application_tracer.enabled = False
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_payload_feature_flag_off(self):
        self.transaction._settings.feature_flag = set()
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_empty_payload(self):
        with self.transaction:
            payload = {}
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
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_create_after_accept_correct_payload(self):
        with self.transaction:
            inbound_payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(
                    inbound_payload)
            assert result
            outbound_payload = \
                    self.transaction.create_distributed_tracing_payload()
            data = outbound_payload['d']
            assert data['ty'] == 'App'
            assert data['pa'] == '7d3efb1b173fecfa'
            assert data['tr'] == 'd6b4ba0c3a712ca'

    def test_sampled_repeated_call(self):
        with self.transaction:
            # priority forced to -1.0 to ensure that .sampled becomes False
            self.transaction._priority = -1.0
            self.transaction._compute_sampled_and_priority()
            assert self.transaction.sampled is False
            assert self.transaction.priority == -1.0

    def test_sampled_create_payload(self):
        with self.transaction:
            self.transaction._priority = 1.0
            payload = self.transaction.create_distributed_tracing_payload()

            assert payload['d']['sa'] is True
            assert self.transaction.sampled is True

            assert payload['d']['pr'] == 2.0
            assert self.transaction.priority == 2.0

    def test_sampled_accept_payload(self):
        payload = {
            'v': [0, 1],
            'd': {
                'ty': 'Mobile',
                'ac': '1',
                'ap': '2827902',
                'pa': '5e5733a911cfbc73',
                'id': '7d3efb1b173fecfa',
                'tr': 'd6b4ba0c3a712ca',
                'ti': 1518469636035,
                'sa': True,
                'pr': 1.8
            }
        }

        with self.transaction:
            self.transaction.accept_distributed_trace_payload(payload)

            assert self.transaction.sampled is True
            assert self.transaction.priority == 1.8

    def test_sampled_true_and_priority_missing(self):
        payload = {
            'v': [0, 1],
            'd': {
                'ty': 'Mobile',
                'ac': '1',
                'ap': '2827902',
                'pa': '5e5733a911cfbc73',
                'id': '7d3efb1b173fecfa',
                'tr': 'd6b4ba0c3a712ca',
                'ti': 1518469636035,
                'sa': True,
            }
        }

        with self.transaction:
            self.transaction.accept_distributed_trace_payload(payload)

            # If priority is missing, sampled should not be set
            assert self.transaction.sampled is None

            # Priority should not be set if missing
            assert self.transaction.priority is None

    def test_priority_but_sampled_missing(self):
        payload = {
            'v': [0, 1],
            'd': {
                'ty': 'Mobile',
                'ac': '1',
                'ap': '2827902',
                'pa': '5e5733a911cfbc73',
                'id': '7d3efb1b173fecfa',
                'tr': 'd6b4ba0c3a712ca',
                'ti': 1518469636035,
                'pr': 0.8,
            }
        }

        with self.transaction:
            self.transaction.accept_distributed_trace_payload(payload)

            # Sampled remains uncomputed
            assert self.transaction.sampled is None

            # Priority should be set to payload priority
            assert self.transaction.priority == 0.8

    def test_sampled_becomes_true(self):
        with self.transaction:
            self.transaction._priority = 1.0
            self.transaction._compute_sampled_and_priority()
            assert self.transaction.sampled is True
            assert self.transaction.priority == 2.0
            assert self.transaction.sampled is True
            assert self.transaction.priority == 2.0

    def test_sampled_becomes_false(self):
        with self.transaction:
            # priority forced to -1.0 to ensure that .sampled becomes False
            self.transaction._priority = -1.0
            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == -1.0
            assert self.transaction.sampled is False
            assert self.transaction.priority == -1.0

    def test_compute_sampled_true_multiple_calls(self):
        with self.transaction:
            # Force sampled to become true
            self.transaction._priority = 1.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is True
            assert self.transaction.priority == 2.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is True
            assert self.transaction.priority == 2.0

    def test_compute_sampled_false_multiple_calls(self):
        with self.transaction:
            # Force sampled to become true
            self.transaction._priority = -1.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == -1.0

            self.transaction._compute_sampled_and_priority()

            assert self.transaction.sampled is False
            assert self.transaction.priority == -1.0


class TestTransactionDeterministic(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        environ = {'REQUEST_URI': '/transaction_apis'}
        mock_app = MockApplication()

        self.transaction = WebTransaction(mock_app, environ)
        self.transaction._settings.cross_application_tracer.enabled = True
        self.transaction._settings.feature_flag = set(['distributed_tracing'])

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_sampling_probability_returns_None(self):
        with self.transaction:
            self.transaction._priority = 1.0
            self.transaction._compute_sampled_and_priority()
            assert self.transaction.sampled is False
            assert self.transaction.priority == 1.0


class TestTransactionComputation(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        super(TestTransactionComputation, self).setUp()

        environ = {'REQUEST_URI': '/transaction_computation'}
        self.transaction = WebTransaction(application, environ)
        self.transaction._settings.feature_flag = set(['distributed_tracing'])

    def test_sampled_is_always_computed(self):
        with self.transaction:
            pass

        assert self.transaction.sampled is not None
        assert self.transaction.priority is not None


if __name__ == '__main__':
    unittest.main()
