from newrelic.core.internal_metrics import InternalTrace, InternalTraceContext
from newrelic.core.stats_engine import CustomMetrics


def test_metric_created_on_exit():
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        t = InternalTrace('foobar')
        t.__enter__()
        assert 'foobar' not in internal_metrics
        internal_metrics.reset_metric_stats()
        t.__exit__(None, None, None)
        assert 'foobar' in internal_metrics
