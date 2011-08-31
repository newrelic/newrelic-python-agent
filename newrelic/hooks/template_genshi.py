import types

from newrelic.api import (wrap_object, transaction, FunctionTraceWrapper)

import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.function_trace

class stream_wrapper(object):
    def __init__(self, stream, filepath):
        self.__stream = stream
        self.__filepath = filepath
    def render(self, *args, **kwargs):
        return newrelic.api.function_trace.FunctionTraceWrapper(
                self.__stream.render, self.__filepath,
                'Template/Render')(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(self.__stream, name)

class wrap_template(object):
    def __init__(self, wrapped):
        self._nr_next_object = wrapped
    def __call__(self, *args, **kwargs):
        current_transaction = newrelic.api.transaction.transaction()
        if current_transaction:
            return stream_wrapper(self._nr_next_object(*args, **kwargs),
                                  args[0].filepath)
        else:
            return self._nr_next_object(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(self._nr_next_object, name)

def instrument(module):

    if module.__name__ == 'genshi.template.base':

        newrelic.api.object_wrapper.wrap_object(
                module, 'Template.generate', wrap_template)
