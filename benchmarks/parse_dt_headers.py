import json
from benchmarks.util import MockApplication

from newrelic.api.transaction import Transaction

INBOUND_TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"

INBOUND_NR_TRACESTATE = (
    "1@nr=0-0-1349956-41346604-27ddd2d8890283b4-b28be285632bbc0a-"
    "1-1.1273-1569367663277"
)

W3C_TRACEPARENT_ONLY = {"traceparent": INBOUND_TRACEPARENT}

W3C_HEADER = {"traceparent": INBOUND_TRACEPARENT,
              "tracestate": INBOUND_NR_TRACESTATE}

NR_PAYLOAD = {
    "v": [0, 1],
    "d": {
        "ac": "1",
        "ap": "2827902",
        "id": "7d3efb1b173fecfa",
        "pa": "5e5733a911cfbc73",
        "pr": 10.001,
        "sa": True,
        "ti": 1518469636035,
        "tr": "d6b4ba0c3a712ca",
        "ty": "App",
    },
}

NR_HEADER = {"newrelic": json.dumps(NR_PAYLOAD)}


class AcceptDistributedTraceHeaders(object):
    def setup(self):
        app = MockApplication(
            settings={
                "account_id": "1",
                "primary_application_id": "1",
                "trusted_account_key": "9000",
                "distributed_tracing.enabled": True,
            }
        )
        self.transaction = Transaction(app)

    def time_newrelic(self):
        self.transaction.accept_distributed_trace_headers(NR_HEADER)


class AcceptDistributedTraceHeadersW3C(object):
    def setup(self):
        app = MockApplication(
            settings={
                "account_id": "1",
                "primary_application_id": "1",
                "trusted_account_key": "9000",
                "distributed_tracing.enabled": True,
            }
        )
        self.transaction = Transaction(app)

    def time_w3c_traceparent_only(self):
        self.transaction.accept_distributed_trace_headers(
                W3C_TRACEPARENT_ONLY)

    def time_w3c_traceparent_and_tracestate(self):
        self.transaction.accept_distributed_trace_headers(
                W3C_HEADER)
