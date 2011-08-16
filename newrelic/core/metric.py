import collections

Metric = collections.namedtuple('Metric', ['name', 'scope'])

ApdexMetric = collections.namedtuple('ApdexMetric',
        ['name', 'overflow', 'forced', 'satisfying', 'tolerating',
        'frustrating'])

TimeMetric = collections.namedtuple('TimeMetric',
        ['name', 'scope', 'overflow', 'forced', 'duration', 'exclusive'])

ValueMetric = collections.namedtuple('ValueMetric',
        ['name', 'value'])

# NOTE: currently used only for tests
def new_metric(name, scope=""):
     return Metric(name, scope)
