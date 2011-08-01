'''
Created on Jul 26, 2011

@author: sdaubin
'''

import collections

def new_metric(name, scope=u""):
    return Metric(name,scope)

Metric = collections.namedtuple('BaseMetric', [u'name',u'scope'])