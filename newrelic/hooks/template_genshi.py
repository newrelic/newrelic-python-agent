import types

from newrelic.api import (wrap_object, transaction, FunctionTraceWrapper,
                            ObjectWrapper)

import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.function_trace

class stream_wrapper(newrelic.api.object_wrapper.ObjectWrapper):
    def __init__(self, stream, filepath):
        newrelic.api.object_wrapper.ObjectWrapper.__init__(self, stream)
        self.__filepath = filepath
    def render(self, *args, **kwargs):
        return newrelic.api.function_trace.FunctionTraceWrapper(
                self.__last_object__.render, self.__filepath,
                'Template/Render')(*args, **kwargs)

class wrap_template(newrelic.api.object_wrapper.ObjectWrapper):
    def __call__(self, *args, **kwargs):
        current_transaction = newrelic.api.transaction.transaction()
        if current_transaction:
            return stream_wrapper(self.__next__object__(*args, **kwargs),
                                  args[0].filepath)
        else:
            return self.__next__object__(*args, **kwargs)

def instrument(module):

    if module.__name__ == 'genshi.template.base':

        newrelic.api.object_wrapper.wrap_object(
                module, 'Template.generate', wrap_template)
