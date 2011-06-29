import sys

import _newrelic

__all__ = [ 'FunctionProfile', 'FunctionProfileWrapper', 'function_profile',
            'wrap_function_profile' ]

# Temporary Python implementation of function profiler as proof of
# concept. This is currently not compatible with coroutines and will not
# do anything if detected that coroutines being used for current web
# transaction.
#
# Don't use this submodule directly, use the names listed above which
# are imported automatically into the 'newrelic.agent' submodule. It is
# those names which will persist if this is retained and moved into a C
# code implementation. No guarantees this feature will be kept though.
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

        transaction = _newrelic.transaction()
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

            function_trace = _newrelic.FunctionTrace(transaction,
                    name=name, scope="Python/Profile",
                    interesting=self.interesting)
            function_trace.__enter__()
            self.function_traces.append(function_trace)

        elif event in ['return', 'c_return']:
            function_trace = self.function_traces.pop()
            if function_trace:
                function_trace.__exit__(None, None, None)

class FunctionProfileWrapper(_newrelic.ObjectWrapper):

    def __init__(self, wrapped, interesting=False, depth=5):
        _newrelic.ObjectWrapper.__init__(self, wrapped)
        self.interesting = interesting
        self.depth = depth

    def __call__(self, *args, **kwargs):
        transaction = _newrelic.transaction()
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

def wrap_function_profile(module, object_name, interesting=False, depth=5):
    (parent_object, attribute_name, object) = _newrelic.resolve_object(
            module, object_name)
    setattr(parent_object, attribute_name, FunctionProfileWrapper(
            object, interesting, depth))
