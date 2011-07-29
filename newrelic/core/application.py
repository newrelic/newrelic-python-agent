'''
Created on Jul 28, 2011

@author: sdaubin
'''
from newrelic.core.remote import NewRelicService
from newrelic.core.stats import StatsDict
from newrelic.core.metric import new_metric

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
        if (connected):
            self._stats_dict = StatsDict(self._service.configuration)
                
        return connected
        
    def merge_stats(self,stats):
        if self._stats_dict:
            # FIXME lock
            self._stats_dict.merge(stats)
            return True
        else:
            return False
        
    def _harvest_and_reset_stats(self):
        # FIXME lock
        stats = self._stats_dict
        self._stats_dict = StatsDict(self._service.configuration)
        return stats
        
    def record_cpu_stats(self,stats):
        stat = stats.get_time_stats(new_metric("CPUTest"))
        stat.record(5,5)

    def harvest(self,connection):
        stats = self._harvest_and_reset_stats()
        self.record_cpu_stats(stats)
        success = False
        try:
            if self._service.connected():
                pass
        finally:
            if not success:
                self.merge_stats(stats)