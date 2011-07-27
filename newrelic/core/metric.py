'''
Created on Jul 26, 2011

@author: sdaubin
'''

class Metric(object):
    '''
    classdocs
    '''


    def __init__(self, name, scope=""):
        '''
        Constructor
        '''
        self._name = name
        self._scope = scope

    def get_name(self):
        return self.__name


    def get_scope(self):
        return self.__scope

        
    def __eq__(self, other):
        return self._name is other._name and self._scope is other._scope

    def __hash__(self):
        return hash(self._name) + hash(self._scope) # FIXME
    
    name = property(get_name, None, None, "The name of this metric")
    scope = property(get_scope, None, None, "The scope of the metric (the context in which it was created)")    