import collections

Metric = collections.namedtuple('Metric', ['name', 'scope'])

ApdexMetric = collections.namedtuple('ApdexMetric',
        ['name', 'scope', 'overflow', 'forced', 'satisfying', 'tolerating',
        'frustrating'])

TimeMetric = collections.namedtuple('TimeMetric',
        ['name', 'scope', 'overflow', 'forced', 'duration', 'exclusive'])

ValueMetric = collections.namedtuple('ValueMetric',
        ['name', 'scope', 'overflow', 'forced', 'value'])
