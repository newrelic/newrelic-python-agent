'''
Created on Jul 29, 2011

@author: sdaubin
'''

import os,time,multiprocessing

from newrelic.core.metric import Metric 

CPU_USER_TIME = Metric(u"CPU/User Time",u"")
CPU_USER_UTILIZATION = Metric(u"CPU/User/Utilization",u"")

'''
CPU times are not sampled
'''
class CPUTimes(object):
    def __init__(self):
        self._last_timestamp = time.time()
        self._times = os.times()
        
    def record(self, stats_dict):
        now = time.time()
        new_times = os.times()
        
        elapsed_time = now - self._last_timestamp
         
        user_time = new_times[0] - self._times[0]
        
        utilization = user_time / (elapsed_time*multiprocessing.cpu_count())
        
        stats_dict.get_time_stats(CPU_USER_TIME).record(user_time)
        stats_dict.get_time_stats(CPU_USER_UTILIZATION).record(utilization)
        
        self._last_timestamp = now
        self._times = new_times
        
#os.times()