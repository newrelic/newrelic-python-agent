'''
Created on Jul 28, 2011

@author: sdaubin
'''
from newrelic.core.remote import NewRelicService
from newrelic.core.stats import StatsDict

class Application(object):
    '''
    classdocs
    '''


    def __init__(self,remote,app_names):
        '''
        Constructor
        '''
        self._app_names = app_names
        self._remote = remote
        self._service = NewRelicService(remote, app_names)
        self._stats_dict = None
        
    def connect(self):
        connected = self._service.connect()
        return connected
        
    def merge_stats(self,stats):
        if self._stats_dict:
            self._stats_dict.merge(stats)
            return True
        else:
            return False
        
    def record_cpu_stats(self):
        pass

    def harvest(self,connection):
        self.record_cpu_stats()
        if self._service.connected():
            pass