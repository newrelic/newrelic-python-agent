import logging
from benchmarks.util import MockApplication, MockTransaction
from newrelic.api.log import NewRelicContextFormatter
from newrelic.core.trace_cache import trace_cache

NR_FORMATTER = NewRelicContextFormatter("%(module)s %(message)s")
DEFAULT_FORMATTER = logging.Formatter("%(module)s %(message)s")
LOG_DICT = {
    "name": __name__,
    "level": logging.INFO,
    "pathname": __file__,
    "lineno": 14,
    "msg": "log message",
    "exc_info": None,
}
LOG_RECORD = logging.makeLogRecord(LOG_DICT)


class TimeLogFormatting(object):
    def time_default_formatter(self):
        DEFAULT_FORMATTER.format(LOG_RECORD)

    def time_new_relic_context_formatter_no_transaction(self):
        NR_FORMATTER.format(LOG_RECORD)


class TimeLogFormattingActiveTransaction(object):
    def setup(self):
        settings = {"app_name": "Benchmark", "entity_guid": "ENTITY_GUID"}
        app = MockApplication(settings)
        self.app = app
        txn = MockTransaction(app, thread_id=trace_cache().current_thread_id())
        txn.ignore_transaction = False
        txn._trace_id = "MOCK_TRACE_ID"
        self.txn = txn

    def teardown(self):
        self.txn.current_span.drop_trace()

    def time_new_relic_context_formatter_active_transaction(self):
        NR_FORMATTER.format(LOG_RECORD)
