import os
import sys
import time
import threading
import zlib
import base64
import traceback

import newrelic
from newrelic.api.transaction import Transaction
import newrelic.lib.simplejson as simplejson

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

_MethodData = namedtuple('_MethodData',
        ['file_name', 'method_name', 'line_no'])

AGENT_DIR = os.path.dirname(newrelic.__file__) + '/'
NODE_LIMIT = 20000

# Config variables

USE_REAL_LINE_NUMBERS = False
ADD_REAL_LINE_LEAF_NODE = True

class ProfileNode(object):
    """This class provides the node used to construct the call tree.
    """
    node_count = 0
    def __init__(self, method_data):
        self.method = method_data
        self.call_count = 0
        self.non_call_count = 0  # only used by Java, never updated for python
        self.children = {}   # key is _MethodData and value is ProfileNode
        self.ignore = False
        ProfileNode.node_count += 1

    def jsonable(self):
        """
        Return Serializable data for json.
        """
        return [self.method, self.call_count, self.non_call_count,
                [x for x in self.children.values() if not x.ignore]]

class ThreadProfiler(object):
    def __init__(self, profile_id, sample_period=0.1, duration=300,
            profile_agent_code=False):
        self._profiler_thread = threading.Thread(target=self._profiler_loop,
                name='NR-Profiler-Thread')
        self._profiler_thread.setDaemon(True)
        self._profiler_shutdown = threading.Event()

        self.profile_id = profile_id
        self._sample_count = 0
        self.start_time = 0
        self.stop_time = 0

        # call_buckets is a dict with 4 buckets. Each bucket's values is a dict
        # that can hold multiple call trees. The dict's key is _MethodData and
        # the value is the root of the call tree (a ProfileNode).
        self.call_buckets = {'REQUEST': {}, 'AGENT': {}, 'BACKGROUND': {},
                'OTHER': {}}
        self.sample_period = sample_period
        self.duration = duration
        self.profile_agent_code = profile_agent_code
        self.node_list = []
        ProfileNode.node_count = 0  # Reset node count to zero

    def _profiler_loop(self):
        """
        This is an infinite loop running in a background thread that wakes up
        every 100ms and calls _run_profiler(). It does this for 'duration'
        seconds and shutsdown the thread.
        """
        while True:
            if self._profiler_shutdown.isSet():
                return
            self._profiler_shutdown.wait(self.sample_period)
            self._run_profiler()
            if (time.time() - self.start_time) >= self.duration:
                self.stop_profiling()

    def _run_profiler(self):
        """
        Collect stacktraces for each thread and update the appropriate call-
        tree bucket.
        """
        self._sample_count += 1
        stacks = collect_thread_stacks()
        for thread_id, stack_trace in stacks.items():
            thr = threading._active.get(thread_id)
            th_type = classify_thread(thr)
            if th_type is None:  # Thread category not found
                continue
            if (th_type is 'AGENT') and (self.profile_agent_code is False):
                continue
            self._update_call_tree(self.call_buckets[th_type], stack_trace)

    def _update_call_tree(self, bucket, stack_trace):
        """
        Merge a stack trace to a call tree in the bucket. If no appropriate
        call tree is found then create a new call tree. An appropriate call
        tree will have the same root node as the last method in the stack
        trace. Methods from the stack trace are pulled from the end one at a
        time and merged with the call tree recursively.
        """
        if not stack_trace:
            return
        method = stack_trace.pop()
        call_tree = bucket.get(method)
        if call_tree is None:
            call_tree = bucket[method] = ProfileNode(method)
        call_tree.call_count += 1
        return self._update_call_tree(call_tree.children, stack_trace)
    
    def start_profiling(self):
        self.start_time = time.time()
        self._profiler_thread.start()

    def stop_profiling(self, forced=False):
        self.stop_time = time.time()
        self._profiler_shutdown.set()
        if forced:
            self._profiler_thread.join(self.sample_period)

    def profile_data(self):
        """
        Return the profile data once the thread profiler has finished otherwise 
        return None.
        """
        if self._profiler_thread.isAlive():
            return None
        call_data = {}
        thread_count = 0
        self._prune_trees(NODE_LIMIT)  # Prune the tree if necessary
        for bucket_type, bucket in self.call_buckets.items():
            if not bucket.values():  # Skip empty buckets
                continue
            call_data[bucket_type] = bucket.values()
            thread_count += len(bucket)
        json_data = simplejson.dumps(call_data, default=lambda o: o.jsonable(),
                ensure_ascii=True, encoding='Latin-1',
                namedtuple_as_object=False)
        encoded_data = base64.standard_b64encode(zlib.compress(json_data))
        profile = [[self.profile_id, self.start_time*1000, self.stop_time*1000,
            self._sample_count, encoded_data, thread_count, 0]]
        return profile

    def _prune_trees(self, limit):
        """
        Prune all the call tree buckets if the number of nodes is greater than 
        NODE_LIMIT. 

        Algo:
        * Add every node in each call tree to a list. 
        * Reverse sort the list by call count. 
        * Set the ignore flag on nodes that are above the NODE_LIMIT threshold
        """
        if ProfileNode.node_count < limit:
            return
        for bucket in self.call_buckets.values():
            for call_tree in bucket.values():
                self._node_to_list(call_tree)
        self.node_list.sort(key=lambda x: x.call_count, reverse=True)
        for node in self.node_list[limit:]:
            node.ignore = True

    def _node_to_list(self, node):
        """
        Walk the call tree and add each node to the node_list.
        """
        if not node:
            return 
        self.node_list.append(node)
        for child_node in node.children.values():
            self._node_to_list(child_node)

def classify_thread(thr):
    """
    Classify the thread whether it's a Web Request, Background or Agent
    thread and return the appropriate bucket to save the stack trace.
    """
    if thr is None:  # Thread is not active
        return None
    # NR thread
    if thr.getName().startswith('NR-'):
        return 'AGENT'

    transaction = Transaction._lookup_transaction(thr)
    if transaction is None:
        return 'OTHER'
    elif transaction.background_task:
        return 'BACKGROUND'
    else:
        return 'REQUEST'
    return None


def collect_thread_stacks(ignore_agent_frames=True):
    """
    Get the stack traces of each thread and record it in a hash with 
    thread_id as key and a list of _MethodData objects as value.
    """
    stack_traces = {}
    for thread_id, frame in sys._current_frames().items():
        thr = threading._active.get(thread_id)
        thr_type = classify_thread(thr)
        stack_traces[thread_id] = []
        leaf_node = ADD_REAL_LINE_LEAF_NODE
        while frame:
            real_line = frame.f_lineno
            filename = frame.f_code.co_filename
            func_name = frame.f_code.co_name
            first_line = frame.f_code.co_firstlineno
            line_no = real_line if USE_REAL_LINE_NUMBERS else first_line
            
            frame = frame.f_back # next frame
            if ((thr_type is not 'AGENT') and filename.startswith(AGENT_DIR)
                    and ignore_agent_frames):
                continue   #  Skip agent frame

            if leaf_node:  # Add a synthesized leaf node with real line_no
                stack_traces[thread_id].append(
                        _MethodData(filename, real_line, real_line))
                leaf_node = False

            stack_traces[thread_id].append(
                    _MethodData(filename, func_name, line_no))
    return stack_traces

def fib(n):
    """
    Test recursive function. 
    """
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)

if __name__ == "__main__":
    t = ThreadProfiler(-1, 0.1, 1, profile_agent_code=True)
    t.start_profiling()
    #fib(35)
    import time
    time.sleep(1.1)
    c = zlib.decompress(base64.standard_b64decode(t.profile_data()[0][4]))
    print c
    #print ProfileNode.node_count
