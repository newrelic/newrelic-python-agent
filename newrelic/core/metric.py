try:
    from collections import namedtuple
except ImportError:
    from newrelic.lib.namedtuple import namedtuple

Metric = namedtuple('Metric', ['name', 'scope'])

ApdexMetric = namedtuple('ApdexMetric',
        ['name', 'satisfying', 'tolerating', 'frustrating', 'apdex_t'])

TimeMetric = namedtuple('TimeMetric',
        ['name', 'scope', 'duration', 'exclusive'])
