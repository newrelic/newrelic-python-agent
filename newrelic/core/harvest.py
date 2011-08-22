'''
Created on Jul 28, 2011

@author: sdaubin
'''

import sys
import logging
import Queue
from newrelic.core.nr_threading import schedule_repeating_task,QueueProcessingThread

_logger = logging.getLogger('newrelic.core.harvest')

class Harvester(object):
    def __init__(self,remote,frequency_in_seconds):
        self._harvest_listeners = []
        self._harvest_count = 0
        self._remote = remote
        self._harvest_work_queue = Queue.Queue(10)
        print "Starting harvest thread"
        self._harvest_thread, self._harvest_event = schedule_repeating_task("New Relic Harvest Timer",self._harvest, frequency_in_seconds)

        self._harvest_work_thread = QueueProcessingThread("New Relic Harvest Processing Thread",self._harvest_work_queue)
        self._harvest_work_thread.start()

    def register_harvest_listener(self,listener):
        self._harvest_listeners.append(listener)

    def unregister_harvest_listener(self,listener):
        self._harvest_listeners.remove(listener)

    def clear_harvest_listeners(self):
        self._harvest_listeners[:] = []

    def _harvest(self):

        if self._harvest_thread:
            self._harvest_count += 1

        self._harvest_work_queue.put_nowait(self._do_harvest)

    '''
    Create a New Relic service connection and call harvest() on all of the harvest listeners.  This is
    called on the harvest processing thread.
    '''
    def _do_harvest(self):
        try:
            connection = self._remote.create_connection()
            try:
                for listener in self._harvest_listeners:
                    listener.harvest(connection)
            finally:
                connection.close()
        except:
            _logger.exception('Failed to harvest data.')

    def get_harvest_count(self):
        return self._harvest_count

    def stop(self):

        if self._harvest_event:
            print "Stopping harvest thread"
            self._harvest_event.set()
            self._harvest_thread.join()
            self._harvest_work_thread.stop()
            alive = self._harvest_thread.is_alive()
            self._harvest_event = None
            self._harvest_thread = None
            return not alive
        else:
            # clean up for unit tests
            self._harvest_count = 0

        return False

    harvest_count = property(get_harvest_count)
