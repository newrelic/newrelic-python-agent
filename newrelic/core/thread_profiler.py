import threading
import time
from collections import namedtuple
import zlib
import newrelic.lib.simplejson as simplejson
import base64

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
    def __init__(self, profile_id, resolution, duration):
        self._profiler_thread = threading.Thread(target=self.profiler_loop,
                name='NR-Profiler-Thread')
        self._profiler_thread.setDaemon(True)
        self._profiler_shutdown = threading.Event()

        self.profile_id = profile_id
        self._sample_count = 0
        self.start_time = 0
        self.stop_time = 0
        self.call_trees = {}
        self.resolution = resolution
        self.duration = duration

    def profiler_loop(self):
        while True:
            if self._profiler_shutdown.isSet():
                self._run_profiler()
                return 
            self._profiler_shutdown.wait(self.resolution)
            self._run_profiler()
            if (time.time() - self.start_time) >= self.duration:
                self.stop_profiling()

    def _run_profiler(self):
        self._sample_count += 1
        stacks = collect_thread_stacks()
        for thread_id, stack_trace in stacks.items():
            if thread_id not in self.call_trees.keys():
                self.call_trees[thread_id] = ProfileNode(stack_trace[0])
            node = self.call_trees[thread_id]
            for method_data in stack_trace:
                node = node.add_child(method_data)
    
    def start_profiling(self):
        self.start_time = time.time()
        self._profiler_thread.start()

    def stop_profiling(self):
        self.stop_time = time.time()
        self._profiler_shutdown.set()
        #self._profiler_thread.join(self.resolution)

    def profile_data(self):
        if self._profiler_thread.isAlive():
            return None
        call_trees = self.call_trees.values()
        call_trees.insert(0, {'cpu_time': 1})
        call_data = {"REQUEST": call_trees}
        json_data = simplejson.dumps(call_data, default=alt_serialize,
                ensure_ascii=True, encoding='Latin-1',
                namedtuple_as_object=False)
        encoded_data = base64.standard_b64encode(
                zlib.compress(json_data))
        profile_data = [[ self.profile_id, self.start_time*1000,
            self.stop_time*1000, self._sample_count, encoded_data,
            len(call_trees) , 0]]
        return profile_data

def collect_thread_stacks():
    import sys
    stack_traces = {}
    for thread_id, frame in sys._current_frames().items():
        stack_traces[thread_id] = []
        while frame:
            stack_traces[thread_id].append(_MethodData(frame.f_code.co_filename,
                frame.f_code.co_name, frame.f_code.co_firstlineno))
            frame = frame.f_back
        stack_traces[thread_id].reverse()
    return stack_traces

def alt_serialize(profile_node):
    if isinstance(profile_node, ProfileNode):
        return profile_node.jsonable()
    else:
        return profile_node


if __name__ == "__main__":
    t = ThreadProfiler(-1, 0.1, 1)
    t.start_profiling()
    import time
    time.sleep(2)
    print t.profile_data()
