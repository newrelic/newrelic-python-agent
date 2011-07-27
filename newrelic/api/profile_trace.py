import sys

import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.function_trace

# Temporary Python implementation of function profiler as proof of
# concept. This is currently not compatible with coroutines and will not
# do anything if detected that coroutines being used for current web
# transaction.
#
# Note that this is currently triggering a time calculation bug within
# the core agent library code in some circumstances.

class FunctionProfile(object):

    def __init__(self, interesting, depth):
        self.function_traces = []
        self.interesting = interesting
        self.depth = depth

    def __call__(self, frame, event, arg):
        if event not in ['call', 'c_call', 'return', 'c_return']:
            return

        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return

        co = frame.f_code
        func_name = co.co_name
        func_line_no = frame.f_lineno
        func_filename = co.co_filename

        caller = frame.f_back
        caller_line_no = caller.f_lineno
        caller_filename = caller.f_code.co_filename

        if event in ['call', 'c_call']:
            if len(self.function_traces) >= self.depth:
                self.function_traces.append(None)
                return

            if event == 'call':
                name = 'Call to %s() on line %s of %s from line %s of %s' % \
                        (func_name, func_line_no, func_filename,
                        caller_line_no, caller_filename)
            else:
                name = 'Call to ???() from line %s of %s' % \
                        (func_line_no, func_filename)

            function_trace = newrelic.api.function_trace.FunctionTrace(
                    transaction, name=name, scope="Python/Profile",
                    interesting=self.interesting)
            function_trace.__enter__()
            self.function_traces.append(function_trace)

        elif event in ['return', 'c_return']:
            function_trace = self.function_traces.pop()
            if function_trace:
                function_trace.__exit__(None, None, None)

class FunctionProfileWrapper(newrelic.api.object_wrapper.ObjectWrapper):

    def __init__(self, wrapped, interesting=False, depth=5):
        newrelic.api.object_wrapper.ObjectWrapper.__init__(self, wrapped)
        self.interesting = interesting
        self.depth = depth

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self.__next_object__(*args, **kwargs)
        if transaction.coroutines:
            return self.__next_object__(*args, **kwargs)
        if not hasattr(sys, 'getprofile'):
            return self.__next_object__(*args, **kwargs)
        profiler = sys.getprofile()
        if profiler:
            return self.__next_object__(*args, **kwargs)
        sys.setprofile(FunctionProfile(self.interesting, self.depth))
        try:
            return self.__next_object__(*args, **kwargs)
        finally:
            sys.setprofile(profiler)

def function_profile(interesting=False, depth=5):
    def decorator(wrapped):
        return FunctionProfileWrapper(wrapped, interesting, depth)
    return decorator

def wrap_function_profile(module, object_path, interesting=False, depth=5):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionProfileWrapper, (interesting, depth))
