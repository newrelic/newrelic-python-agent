import types

from newrelic.agent import (wrap_object, transaction, FunctionTraceWrapper,
                            update_wrapper)

class stream_wrapper(object):
    def __init__(self, stream, filepath):
        self.__wrapped__ = stream
        self.__filepath = filepath
        update_wrapper(self, stream)
    def __getattr__(self, name):
        if name == 'render':
            return FunctionTraceWrapper(getattr(self.__wrapped__, name),
                    self.__filepath, 'Template/Render')
        return getattr(self.__wrapped__, name)

class wrap_template(object):
    def __init__(self, wrapped):
        self.__wrapped__ = wrapped
        update_wrapper(self, wrapped)
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, *args, **kwargs):
        current_transaction = transaction()
        if current_transaction:
            return stream_wrapper(self.__wrapped__(*args, **kwargs),
                                  args[0].filepath)
        else:
            return self.__wrapped__(*args, **kwargs)

def instrument(module):

    if module.__name__ == 'genshi.template.base':

        wrap_object(module, 'Template.generate', wrap_template)
