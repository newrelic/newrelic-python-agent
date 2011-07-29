'''
Created on Jul 28, 2011

@author: sdaubin
'''

import threading

def repeat(event, every, action): 
    while True: 
        event.wait(every) 
        if event.isSet(): 
            return 
        action() 


def schedule_repeating_task(thread_name, method, frequency_in_sec):
    ev = threading.Event()
    t = threading.Thread(target=repeat, args=(ev, frequency_in_sec, method))
    t.setName(thread_name)
    t.setDaemon(True)
    t.start()
    return t, ev

            
'''
A thread that executes items from the given work queue.
'''
class QueueProcessingThread(threading.Thread):
    STOP = Exception("STOP THE QUEUE")
    def __init__(self,name,work_queue,error_callback=None):
        threading.Thread.__init__(self,target=self.worker)
        self.name = name
        self._error_callback=error_callback
        self._work_queue = work_queue
        self.setDaemon(True)
        
    def stop(self):
        self._work_queue.put(self._stop_work)
        
    def _stop_work(self):
        raise QueueProcessingThread.STOP
        
    def worker(self):
        run = True
        while run:
            work = self._work_queue.get()
            try:
                work()
            except Exception as ex:
                if QueueProcessingThread.STOP is ex:
                    run = False
                if self._error_callback:
                    self._error_callback(ex)
            self._work_queue.task_done()