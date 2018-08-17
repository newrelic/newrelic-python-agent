from newrelic.api.external_trace import ExternalTrace
from benchmarks.util import (MockApplication, MockTransaction,
        create_incoming_headers)


class CatClassic(object):
    def setup(self):
        app = MockApplication(settings={
            'cross_process_id': '1#1',
            'encoding_key': 'cookies',
        })
        self.transaction = MockTransaction(app)
        self.trace = ExternalTrace(self.transaction, 'foo', 'http://localhost')

        # Add CAT specific transaction attributes
        self.transaction.guid = 'GUID'
        self.transaction.record_tt = False
        self.transaction._trip_id = None
        self.transaction._application = app
        self.transaction._frozen_path = 'path'
        self.transaction._alternate_path_hashes = {}
        self.transaction.synthetics_header = None

        self.response_headers = create_incoming_headers(self.transaction)

    def time_generate_request_headers(self):
        ExternalTrace.generate_request_headers(self.transaction)

    def time_process_response_headers(self):
        self.trace.process_response_headers(self.response_headers)


class DistributedTracing(object):
    def setup(self):
        app = MockApplication(settings={
            'account_id': '1',
            'primary_application_id': '1',
            'trusted_account_key': '9000',
            'distributed_tracing.enabled': True,
        })
        self.transaction = MockTransaction(app)
        self.transaction._application = app
        self.transaction._transaction_metrics = {}
        self.transaction._priority = None
        self.transaction._sampled = None
        self.transaction._trace_id = None
        self.transaction.guid = 'GUID'
        self.transaction.synthetics_header = None

    def time_generate_request_headers(self):
        ExternalTrace.generate_request_headers(self.transaction)


class CatOff(CatClassic):
    def setup(self):
        app = MockApplication(settings={
            'encoding_key': 'cookies',
            'cross_application_tracer.enabled': False,
            'distributed_tracing.enabled': False,
        })
        self.transaction = MockTransaction(app)
        self.trace = ExternalTrace(self.transaction, 'foo', 'http://localhost')
        self.response_headers = create_incoming_headers(self.transaction)
        self.transaction.synthetics_header = None
