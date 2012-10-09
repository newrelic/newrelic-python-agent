import sys
import time
import threading
import zlib
import base64
import traceback

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.lib.simplejson as simplejson

_MethodData = namedtuple('_MethodData',
        ['file_name', 'method_name', 'line_no'])

class ProfileNode(object):
    """This class provides the node used to construct the call tree.
    """
    def __init__(self, method_data):
        self.method = method_data
        self.call_count = 0
        self.non_call_count = 0
        self.children = {}

    def add_child(self, method_data):
        """
        If method_data matches current node or one of the immediate child nodes
        update the call count. Other wise create a new child node and set call
        count to 1.
        """
        if method_data == self.method:
            self.call_count += 1
            return self
        else:
            try:
                self.children[method_data].call_count += 1
            except KeyError:
                self.children[method_data] = ProfileNode(method_data)
                self.children[method_data].call_count += 1
            return self.children[method_data]

    def jsonable(self):
        """
        Return Serializable data for json.
        """
        return [self.method, self.call_count, self.non_call_count,
                self.children.values()]

class ThreadProfiler(object):
    def __init__(self, profile_id, sample_period=0.1, duration=300,
            profile_agent_code=False, only_runnable_threads=False):
        self._profiler_thread = threading.Thread(target=self.profiler_loop,
                name='NR-Profiler-Thread')
        self._profiler_thread.setDaemon(True)
        self._profiler_shutdown = threading.Event()

        self.profile_id = profile_id
        self._sample_count = 0
        self.start_time = 0
        self.stop_time = 0
        self.call_trees = {'REQUEST': {}, 
                'AGENT': {}, 
                'BACKGROUND': {}, 
                'OTHER': {}, 
                }
        self.sample_period = sample_period
        self.duration = duration
        self.profile_agent_code = profile_agent_code
        self.only_runnable_threads = only_runnable_threads


    def profiler_loop(self):
        while True:
            if self._profiler_shutdown.isSet():
                self._run_profiler()
                return 
            self._profiler_shutdown.wait(self.sample_period)
            self._run_profiler()
            if (time.time() - self.start_time) >= self.duration:
                self.stop_profiling()

    def get_call_tree(self, thr):
        if thr is None:  # Thread is not active
            return None
        if thr.isDaemon():
            if 'NR-' in thr.name:
                if self.profile_agent_code:
                    return self.call_trees['AGENT']
                else:
                    return None
            else:
                return self.call_trees['BACKGROUND']
        else:
            return self.call_trees['REQUEST']

    def _run_profiler(self):
        self._sample_count += 1
        for thread_id, frame in sys._current_frames().items():
            thr = threading._active.get(thread_id)
            call_trees = self.get_call_tree(thr)
            if call_trees is None:
                continue  # Appropriate call tree not found, ignore the thread
            node = call_trees.get(thread_id)
            for file_name, line_no, func_name, text in traceback.extract_stack(
                    frame):
                method_data = _MethodData(file_name, func_name, line_no)
                if node is None:
                    call_trees[thread_id] = ProfileNode(method_data)
                    node = call_trees.get(thread_id)
                node = node.add_child(method_data)
    
    def start_profiling(self):
        self.start_time = time.time()
        self._profiler_thread.start()

    def stop_profiling(self, forced=False):
        self.stop_time = time.time()
        self._profiler_shutdown.set()
        if forced:
            self._profiler_thread.join(self.sample_period)

    def profile_data(self):
        if self._profiler_thread.isAlive():
            return None
        call_data = {}
        thread_count = 0
        for thread_type, call_tree in self.call_trees.items():
            stack = call_tree.values()
            stack.insert(0, {'cpu_time': 1})
            call_data[thread_type] = stack
            thread_count += len(call_tree)
        json_data = simplejson.dumps(call_data, default=alt_serialize,
                ensure_ascii=True, encoding='Latin-1',
                namedtuple_as_object=False)
        encoded_data = base64.standard_b64encode(zlib.compress(json_data))
        profile = [[self.profile_id, self.start_time*1000, self.stop_time*1000,
            self._sample_count, encoded_data, thread_count, 0]]
        return profile

def alt_serialize(data):
    """
    Alternate serializer for the ProfileNode object. Used by the json.dumps
    """
    if isinstance(data, ProfileNode):
        return data.jsonable()
    else:
        return data

if __name__ == "__main__":
    t = ThreadProfiler(-1, 0.1, 1, profile_agent_code=True)
    t.start_profiling()
    import time
    time.sleep(1.1)
    #print t.profile_data()
    print zlib.decompress(base64.standard_b64decode(t.profile_data()[0][4]))
