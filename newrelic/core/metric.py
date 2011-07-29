'''
Created on Jul 26, 2011

@author: sdaubin
'''

import collections

def new_metric(name, scope=""):
    return Metric(name,scope)

class Metric(collections.namedtuple('BaseMetric', ['name','scope'])):
    '''
    classdocs
    '''
        
    def __eq__(self, other):
        return self.name is other.name and self.scope is other.scope

    def __hash__(self):
        return hash(self.name) + hash(self.scope) # FIXME
    
    def to_json(self):
        return self._asdict()
