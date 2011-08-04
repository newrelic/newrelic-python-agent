'''
Created on Jul 28, 2011

@author: sdaubin
'''
from newrelic.core.remote import NewRelicService
from newrelic.core.stats import StatsDict
from newrelic.core.metric import new_metric
from newrelic.core.samplers import CPUTimes
import Queue,threading
from newrelic.core.nr_threading import QueueProcessingThread

INSTANCE_REPORTING_METRIC = new_metric(u"Instance/Reporting")

class Application(object):
    '''
    classdocs
    '''


    def __init__(self, remote, name, clusters):
        '''
        Constructor
        '''

	# FIXME What is the appropriate term for these
	# secondary application names to report as other
	# than clusters. Want to maintain them as a
	# distinct item from primary name.

        self._name = name
        self._clusters = sorted(set(clusters))
        self._app_names = [name] + clusters

        # _metric_ids is always accessed from the harvest thread, so it requires no synchronization
        self._metric_ids = {}
        self._remote = remote
        self._service = NewRelicService(remote, self._app_names)
        self._stats_lock = threading.Lock()
        self._stats_dict = None
        # we could pull this queue and its processor up to the agent
        self._work_queue = Queue.Queue(10)
        self._work_thread = QueueProcessingThread(("New Relic Worker Thread (%s)" % str(self._app_names)),self._work_queue)
        self._work_thread.start()
        self._work_queue.put_nowait(self.connect)
        self._cpu_times = CPUTimes()

    @property
    def name(self):
        return self._name

    @property
    def clusters(self):
        return self._cluster

    def stop(self):
        self._work_thread.stop()

    def get_configuration(self):
        return self._service.configuration

    def connect(self):
        print "Connecting to the New Relic service"
        connected = self._service.connect()
        if connected:
            self._stats_dict = StatsDict(self._service.configuration)
            print "Connected to the New Relic service"

        return connected

    def merge_stats(self,stats):
        try:
            self._stats_lock.acquire()
            if self._stats_dict:
                self._stats_dict.merge(stats)
                return True
            else:
                return False
        finally:
            self._stats_lock.release()

    def _harvest_and_reset_stats(self):
        # FIXME lock
        if self._stats_dict is not None:
            stats = self._stats_dict
            self._stats_dict = StatsDict(self._service.configuration)
            return stats

    def record_cpu_stats(self,stats):
        if stats is not None:
            print "Recording CPU metrics"
            self._cpu_times.record(stats)

    def parse_metric_response(self,res):
        print "Metric data response: %s" % str(res)
        return
        # FIXME this code isn't working for some reason
        for m in res:
            metric = new_metric(m[0]["name"],m[0]["scope"])
            self._metric_ids[metric] = m[1]
        print self._metric_ids

    def harvest(self,connection):
        print "Harvesting"
        try:
            self._stats_lock.acquire()
            stats = self._harvest_and_reset_stats()
        finally:
            self._stats_lock.release()
        self.record_cpu_stats(stats)
        stats.get_time_stats(INSTANCE_REPORTING_METRIC).record(0)
        print stats
        success = False
        try:
            if self._service.connected():
                self.parse_metric_response(self._service.send_metric_data(connection,stats.metric_data(self._metric_ids)))
        finally:
            if not success:
                self.merge_stats(stats)

    configuration = property(get_configuration, None, None, None)
