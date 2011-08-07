'''
Created on Jul 28, 2011

@author: sdaubin
'''
from newrelic.core.remote import NewRelicService
from newrelic.core.stats import StatsDict
from newrelic.core.metric import Metric
from newrelic.core.samplers import CPUTimes
import Queue,threading
from newrelic.core.nr_threading import QueueProcessingThread

INSTANCE_REPORTING_METRIC = Metric(u"Instance/Reporting", "")

class Application(object):
    '''
    classdocs
    '''


    def __init__(self, remote, app_name, linked_applications=[]):
        '''
        Constructor
        '''

        self._app_name = app_name
        self._linked_applications = sorted(set(linked_applications))

        self._app_names = [app_name] + linked_applications

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
        return self._app_name

    @property
    def linked_applications(self):
        return self._linked_applications

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

    def record_metric(self, name, value):
        # FIXME This is where base metric needs to be queued up.

        print 'METRIC', name, value

    def record_transaction(self, data):

	# FIXME The application object perhaps needs to maintain an
	# activation counter. This would be incremented after each
	# connect to core application and updated server side
	# configuration available. The counter number should then be
	# pushed into the application specific settings object and the
	# higher level instrumentation layer should then supply the
	# counter value in the TransactionNode root object for the raw
	# transaction data. That way the code here could make a decision
	# whether the data should be thrown away as it relates to a
	# transaction that started when the application was previously
	# active, but got restarted in between then and when the
	# transaction completed. If we don't do this then we could push
	# through transaction data accumulated based on an old set of
	# application specific configuration settings. This may not be
	# an issue given in most cases the server side configuration
	# wouldn't change but should be considered. No harm in adding
	# the counter even if not ultimately needed. The core
	# application could even be what doles out the counter or
	# identifying value for that configuration snapshot and record
	# it against the agent run details stored in core application
	# database rather than it be generated internally using a
	# counter. The value could change on each request or only
	# increment when server side sees a change in server side
	# application configuration. If only changes when configuration
	# changes, wouldn't matter then that request started with one
	# configuration and finished after application had been
	# restarted.

        print 'TRANSACTION', data

        for metric in data.apdex_metrics():
            print 'APDEX', metric
            self._stats_dict.get_apdex_stats(Metric(metric.name,
                    metric.scope)).merge(metric)

        for metric in data.time_metrics():
            print 'TIME', metric
            self._stats_dict.get_time_stats(Metric(metric.name,
                    metric.scope)).record(metric.duration, metric.exclusive)

        # FIXME Force harvest on each request for now as otherwise
        # doesn't appear to be running.

        connection = self._remote.create_connection()
        self.harvest(connection)

    def record_cpu_stats(self,stats):
        if stats is not None:
            print "Recording CPU metrics"
            self._cpu_times.record(stats)

    def parse_metric_response(self,res):
        print "Metric data response: %s" % str(res)
        return
        # FIXME this code isn't working for some reason
        for m in res:
            metric = Metric(m[0]["name"],m[0]["scope"])
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
