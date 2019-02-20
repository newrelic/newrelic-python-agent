import functools
from newrelic.api.background_task import BackgroundTask
from newrelic.api.database_trace import DatabaseTrace

from newrelic.core.config import finalize_application_settings
from newrelic.core.stats_engine import StatsEngine


class MockApplication(object):
    def __init__(self, name='Python Application', settings={}):
        final_settings = finalize_application_settings(settings)
        self.global_settings = final_settings
        self.global_settings.enabled = True
        self.settings = final_settings
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None
        self.nodes = []

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        self.nodes.append(data)
        return None

    def compute_sampled(self):
        return True


class Base(object):

    def setup(self, settings={
        'transaction_tracer.transaction_threshold': 0.0
    }, traces=()):
        app = MockApplication(settings=settings)
        txn = BackgroundTask(app, 'foo')
        try:
            with txn:
                for trace in traces:
                    with trace(txn):
                        pass
                raise ValueError("oops")
        except ValueError:
            pass

        self.app = app
        self.stats = StatsEngine()
        self.stats.reset_stats(app.settings)
        self.node = app.nodes.pop()

    def time_record_transaction(self):
        self.stats.record_transaction(self.node)


class Lite(Base):

    def setup(self, settings={
        'error_collector.enabled': False,
        'transaction_tracer.enabled': False,
        'slow_sql.enabled': False,
        'transaction_events.enabled': False,
        'custom_insights_events.enabled': False,
    }):
        super(Lite, self).setup(settings=settings)


class TimeWithDatabaseBase(Base):

    def setup(self, settings={
        'transaction_tracer.enabled': False,
        'slow_sql.enabled': False,
    }):
        traces = [functools.partial(DatabaseTrace, sql='select * from foo')]
        return super(TimeWithDatabaseBase, self).setup(
                settings=settings, traces=traces)


class TimeWithDatabaseSlowSql(TimeWithDatabaseBase):
    def setup(self, settings={
            'transaction_tracer.enabled': False,
            'slow_sql.enabled': True,
            'transaction_tracer.explain_threshold': 0.0,
    }):
        return super(TimeWithDatabaseSlowSql, self).setup(settings=settings)


class TimeWithDatabaseTT(TimeWithDatabaseBase):
    def setup(self, settings={
            'slow_sql.enabled': False,
            'transaction_tracer.explain_threshold': 0.0,
    }):
        return super(TimeWithDatabaseTT, self).setup(settings=settings)
