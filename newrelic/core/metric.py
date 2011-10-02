try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

Metric = namedtuple('Metric', ['name', 'scope'])

ApdexMetric = namedtuple('ApdexMetric',
        ['name', 'overflow', 'forced', 'satisfying', 'tolerating',
        'frustrating'])

TimeMetric = namedtuple('TimeMetric',
        ['name', 'scope', 'overflow', 'forced', 'duration', 'exclusive'])

ValueMetric = namedtuple('ValueMetric',
        ['name', 'value'])

# NOTE: currently used only for tests
def new_metric(name, scope=""):
     return Metric(name, scope)
