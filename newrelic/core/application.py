'''
Created on Jul 28, 2011

@author: sdaubin
'''
from newrelic.core.remote import NewRelicService
from newrelic.core.stats import StatsDict
from newrelic.core.metric import new_metric
import Queue
from newrelic.core.nr_threading import QueueProcessingThread

class Application(object):
    '''
    classdocs
    '''


    def __init__(self,remote,app_names):
        '''
        Constructor
        '''
        self._app_names = app_names
        self._metric_ids = {}
        self._remote = remote
        self._service = NewRelicService(remote, app_names)
        self._stats_dict = None
        self._work_queue = Queue.Queue(10)
        self._work_thread = QueueProcessingThread(("New Relic Worker Thread (%s)" % str(app_names)),self._work_queue)
        self._work_thread.start()
        self._work_queue.put_nowait(self.connect)
        
    def connect(self):
        print "Connecting to the New Relic service"
        connected = self._service.connect()
        if connected:
            self._stats_dict = StatsDict(self._service.configuration)
            print "Connected to the New Relic service"

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
        if self._stats_dict:
            stats = self._stats_dict
            self._stats_dict = StatsDict(self._service.configuration)
            return stats
        
    def record_cpu_stats(self,stats):
        if stats:
            stat = stats.get_time_stats(new_metric("CPUTest"))
            stat.record(5,5)

    def parse_metric_response(self,res):
        pass

    def harvest(self,connection):
        print "Harvesting"
        stats = self._harvest_and_reset_stats()
        self.record_cpu_stats(stats)
        success = False
        try:
            if self._service.connected():
                self.parse_metric_response(self._service.send_metric_data(stats.metric_data(self._metric_ids)))
        finally:
            if not success:
                self.merge_stats(stats)