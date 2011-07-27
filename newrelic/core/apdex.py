'''
Created on Jul 25, 2011

@author: sdaubin
'''

class ApdexSetting(object):
    '''
    classdocs
    '''


    def __init__(self, apdex_t_in_millis):
        '''
        Constructor
        '''
        self._apdex_t = apdex_t_in_millis
        self._apdex_f = apdex_t_in_millis*4
    
    def get_apdex_t(self):
        return self._apdex_t
    
    def get_apdex_f(self):
        return self._apdex_f
    
    apdex_t = property(get_apdex_t)
    apdex_f = property(get_apdex_f)
        