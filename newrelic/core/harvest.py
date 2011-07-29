'''
Created on Jul 28, 2011

@author: sdaubin
'''

import Queue
from newrelic.core.nr_threading import schedule_repeating_task,QueueProcessingThread
from newrelic.core.agent import newrelic_agent

_harvest_thread = None
_harvest_event = None
_harvest_count = 0
_harvest_listeners = []
_harvest_work_thread = None
_harvest_work_queue = Queue.Queue(10)

def register_harvest_listener(listener):
    global _harvest_listeners
    _harvest_listeners.append(listener)

def unregister_harvest_listener(listener):
    global _harvest_listeners
    _harvest_listeners.remove(listener)
    
def clear_harvest_listeners():
    global _harvest_listeners
    _harvest_listeners[:] = []

def start_harvest_thread(frequency_in_seconds):
    global _harvest_thread
    global _harvest_event
    global _harvest_count
    global _harvest_work_thread
    global _harvest_work_queue
    
    if _harvest_thread:
        # FIXME log attempt to start thread twice
        return False
    
    print "Starting harvest thread"
    _harvest_count = 0
    _harvest_thread, _harvest_event = schedule_repeating_task("New Relic Harvest Timer",_harvest, frequency_in_seconds)
    
    _harvest_work_thread = QueueProcessingThread("New Relic Harvest Processing Thread",_harvest_work_queue)
    _harvest_work_thread.start()

    return _harvest_thread.is_alive()
    
def _harvest():
    global _harvest_count
    global _harvest_listeners
    
    if _harvest_thread:
        _harvest_count += 1

    _harvest_work_queue.put(_do_harvest,False,1)
    
'''
Create a New Relic service connection and call harvest() on all of the harvest listeners.  This is
called on the harvest processing thread. 
'''    
def _do_harvest():
    try:
        r = newrelic_agent().remote
        connection = r.create_connection()
        try:
            for listener in _harvest_listeners:
                listener.harvest(connection)
        finally:
            connection.close()
    except Exception as ex:
        print ex
    
def harvest_count():
    global _harvest_count
    return _harvest_count
    
def stop_harvest_thread():
    global _harvest_thread
    global _harvest_event
    global _harvest_count

    if _harvest_event:
        print "Stopping harvest thread"
        _harvest_event.set()
        _harvest_thread.join()
        _harvest_work_thread.stop()
        alive = _harvest_thread.is_alive()
        _harvest_event = None
        _harvest_thread = None
        return not alive
    else:
        # clean up for unit tests
        _harvest_count = 0

    return False
