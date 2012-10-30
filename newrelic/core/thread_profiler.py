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

NODE_LIMIT = 20000

# Class which is used to identify the point in the code where execution
# was occuring when the sample was taken. One of these will exist for
# each stack frame.
#
# Note that the UI was originally written based around the Java agent
# and for Java everything is in a class and so the class refers to the
# method data. For Python we only have access to the function name and
# do not know the class it is in. We thus only use the function name,
# but because in the case of a method of a class, there could be
# multiple methods of the same name defined within different classes, or
# even as a function at global scope, then we add the first line number
# of the code as part of the name. This makes it easier to identify
# which function or method it is rather than trying to work it out from
# execution line.

_MethodData = namedtuple('_MethodData',
        ['file_name', 'method_name', 'line_no'])

# Collection of the actual calls stacks is done by getting access to the
# current stack frames for all threads provided by CPython. If greenlets
# are used this is more complicated as greenlets will not appear in that
# list of stack frames. The stack frames for greenlets are available
# from the greenlet itself, but there is no list of all active greenlets.
# For now we attach the greenlet to the record of any transaction we
# are tracking and get to it that way. For convenience and because we
# need to refer to the transaction objects to categorise what the thread
# is being used for anyway, we put all the code dealing with that in the
# transaction class and we reach up and get the data on active threads
# from it.

USE_REAL_LINE_NUMBERS = True
ADD_REAL_LINE_LEAF_NODE = True
ADD_LINE_TO_FUNC_NAME = True
IGNORE_AGENT_FRAMES = True

AGENT_PACKAGE_DIRECTORY = os.path.dirname(newrelic.__file__) + '/'

def collect_stack_traces():
    """Collects representaions for the stack of each active thread
    within the process. A item is yielded for each thread which consists
    of a tuple with the category of thread and then the stack trace.

    """

    for thread_id, thread_category, frame in Transaction._active_threads():
        stack_trace = []

        # The initial stack frame is the lowest frame or leaf node and
        # we will track back up the stack. For that lowest stack frame
        # we optionally want to introduce a fake node which captures the
        # actual execution line so will be displayed as a separate item
        # in the UI. This makes it easier to identify where in the
        # actual code it was executing.

        leaf_node = ADD_REAL_LINE_LEAF_NODE

        while frame:
            # The value frame.f_code.co_firstlineno is the first line of
            # code in the file for the specified function. The value
            # frame.f_lineno is the actual line which is being executed
            # at the time the stack frame was being viewed.

            filename = frame.f_code.co_filename
            func_name = frame.f_code.co_name
            first_line = frame.f_code.co_firstlineno

            real_line = frame.f_lineno

            # As we experiment with representation of the stack trace in
            # UI, allow line number for each stack frame to either be
            # the actual execution line or start of function. It would
            # appear at this point it should always be execution line.

            line_no = real_line if USE_REAL_LINE_NUMBERS else first_line

            # Set ourselves up to process next frame back up the stack.

            frame = frame.f_back

            # So as to make it more obvious to the user as to what their
            # code is doing, we drop out stack frames related to the
            # agent instrumentation. Don't do this for the agent threads
            # though as we still need to seem them in that case so can
            # debug what the agent itself is doing.

            if IGNORE_AGENT_FRAMES and thread_category != 'AGENT':
                if filename.startswith(AGENT_PACKAGE_DIRECTORY):
                    continue

            if leaf_node:
                # Add the fake leaf node with line number of where the
                # code was executing at the point of the sample. This
                # could be actual Python code within the function, or
                # more likely showing the point where a call is being
                # made into a C function wrapped as Python object. The
                # latter can occur because we will not see stack frames
                # when calling into C functions.

                name = '@%s#%s' % (func_name, real_line)
                method_data = _MethodData(filename, name, line_no)
                stack_trace.append(method_data)

                leaf_node = False

            # Add the actual node for the function being called at this
            # level in the stack frames.

            if ADD_LINE_TO_FUNC_NAME:
                name = '%s#%s' % (func_name, first_line)
            else:
                name = func_name

            method_data = _MethodData(filename, name, line_no)

            stack_trace.append(method_data)

        yield thread_category, stack_trace

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
        for thread_category, stack_trace in collect_stack_traces():
            if thread_category is None:  # Thread category not found
                continue
            if (thread_category == 'AGENT') and (self.profile_agent_code == False):
                continue
            self._update_call_tree(self.call_buckets[thread_category], stack_trace)

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
