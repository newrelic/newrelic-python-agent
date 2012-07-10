import sys
import types

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

    def __init__(self, depth):
        self.function_traces = []
        self.depth = depth

    def __call__(self, frame, event, arg):
        if event not in ['call', 'c_call', 'return', 'c_return']:
            return

        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return

        co = frame.f_code
        func_name = co.co_name
        func_line_no = frame.f_lineno
        func_filename = co.co_filename

        caller = frame.f_back
        caller_line_no = caller.f_lineno
        caller_filename = caller.f_code.co_filename

        # FIXME Doesn't work for C calls. Don't appear to get the
        # correct number of return events.

        #if event in ['call', 'c_call']:
        if event in ['call']:
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
                    transaction, name=name, group="Python/Profile")
            function_trace.__enter__()
            self.function_traces.append(function_trace)

        #elif event in ['return', 'c_return']:
        elif event in ['return']:
            function_trace = self.function_traces.pop()
            if function_trace:
                function_trace.__exit__(None, None, None)

class ProfileTraceWrapper(object):

    def __init__(self, wrapped, depth=5):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_depth = depth

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_name,
                              self._nr_group)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        #if transaction.coroutines:
        #    return self._nr_next_object(*args, **kwargs)
        if not hasattr(sys, 'getprofile'):
            return self._nr_next_object(*args, **kwargs)

        profiler = sys.getprofile()

        if profiler:
            return self._nr_next_object(*args, **kwargs)

        sys.setprofile(FunctionProfile(self._nr_depth))

        try:
            return self._nr_next_object(*args, **kwargs)
        finally:
            sys.setprofile(profiler)

def function_profile(depth=5):
    def decorator(wrapped):
        return ProfileTraceWrapper(wrapped, depth)
    return decorator

def wrap_function_profile(module, object_path, depth=5):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            ProfileTraceWrapper, (depth,))
