'''
Created on Jul 25, 2011

@author: sdaubin
'''

class BaseStats(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
    def has_data(self):
        pass # Override me in derived class

    def merge(self, other_stats):
        pass # Override me in derived class

    def to_json(self):
        pass # Override me in derived class

    def clone(self):
        pass # Override me in derived class
    
class ApdexStats(BaseStats):
    def __init__(self, apdex_setting):
        '''
        Constructor
        '''
        self._satisying = 0
        self._tolerating = 0
        self._frustrating = 0
        self._apdex_setting = apdex_setting
        
    def record_frustrating(self):
        self._frustrating += 1
        
    def record(self, time_in_seconds):
        if time_in_seconds <= self._apdex_setting.apdex_t:
            self._satisying += 1
        elif time_in_seconds <= self._apdex_setting.apdex_f:
            self._tolerating += 1
        else:
            self._frustrating += 1
            
    def has_data(self):
        return self._satisying > 0 or self._tolerating > 0 or self._frustrating > 0

    def merge(self, other_stats):
        self._satisying += other_stats._satisying
        self._tolerating += other_stats._tolerating
        self._frustrating += other_stats._frustrating

    def to_json(self):
        pass # FIXME

    def clone(self):
        s = ApdexStats(self._apdex_setting)
        s._satisying = self._satisying
        s._tolerating = self._tolerating
        s._frustrating = self._frustrating
        return s
            
    def get_satisfying(self):
        return self._satisying    
    def get_tolerating(self):
        return self._tolerating
    def get_frustrating(self):
        return self._frustrating
    
    satisfying = property(get_satisfying)
    tolerating = property(get_tolerating)
    frustrating = property(get_frustrating)

class TimeStats(BaseStats):
    def __init__(self):
        '''
        Constructor
        '''
        self._call_count = 0
        self._total_call_time = 0
        self._total_exclusive_call_time = 0
        self._min_call_time = 0
        self._max_call_time = 0
        
    def record(self, call_time_in_seconds, exclusive_call_time_in_seconds):
        if self._call_count is 0 or self._min_call_time > call_time_in_seconds:
            self._min_call_time = call_time_in_seconds
        if self._max_call_time < call_time_in_seconds:
            self._max_call_time = call_time_in_seconds

        self._call_count += 1
        self._total_call_time += call_time_in_seconds
        self._total_exclusive_call_time += exclusive_call_time_in_seconds
            
    def has_data(self):
        return self._call_count > 0

    def merge(self, other_stats):
        self._call_count += other_stats._call_count
        self._total_call_time += other_stats._total_call_time
        self._total_exclusive_call_time += other_stats._total_exclusive_call_time
        self._min_call_time = min(self._min_call_time, other_stats._min_call_time)
        self._max_call_time = max(self._max_call_time, other_stats._max_call_time)

    def to_json(self):
        pass # FIXME

    def clone(self):
        s = TimeStats()
        s._call_count = self._call_count
        s._max_call_time = self._max_call_time
        s._min_call_time = self._min_call_time
        s._total_call_time = self._total_call_time
        s._total_exclusive_call_time = self._total_exclusive_call_time
        return s
       
    '''
    Accessors
    '''     
    def get_max_call_time(self):
        return self._max_call_time
    def get_min_call_time(self):
        return self._min_call_time        
    def get_total_call_time(self):
        return self._total_call_time     
    def get_total_exclusive_call_time(self):
        return self._total_exclusive_call_time
    def get_call_count(self):
        return self._call_count
    
    '''
    Properties
    '''
    call_count = property(get_call_count)
    max_call_time = property(get_max_call_time)
    min_call_time = property(get_min_call_time)
    total_call_time = property(get_total_call_time)
    total_exclusive_call_time = property(get_total_exclusive_call_time)
    
    
class StatsDict(object):
    def __init__(self, apdex_settings):
        '''
        Constructor
        '''
        self._stats_dict = dict()
        self._apdex_settings = apdex_settings
        
    def get_time_stats(self, key):
        s = self._stats_dict.get(key)
        if s is None:
            s = TimeStats()
            self._stats_dict[key] = s
        return s
    
    def get_apdex_stats(self, key):
        s = self._stats_dict.get(key)
        if s is None:
            s = ApdexStats(self._apdex_settings)
            self._stats_dict[key] = s
        return s
        
    def merge(self, other_stats_dict):
        for k,v in other_stats_dict.iteritems():
            s = self._stats_dict.get(k)
            if s is None:
                self._stats_dict[k] = v.clone()
            else:
                s.merge(v)
    
    
        