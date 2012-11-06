from __future__ import with_statement

import functools
import inspect

from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import (ObjectWrapper, wrap_object)
from newrelic.core.external_node import ExternalNode

class ExternalTrace(TimeTrace):

    def __init__(self, transaction, library, url, method=None):
        super(ExternalTrace, self).__init__(transaction)

        self.library = library
        self.url = url
        self.method = method

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(library=self.library,
                url=self.url, method=self.method)

    def create_node(self):
        return ExternalNode(library=self.library, url=self.url,
                method=self.method, children=self.children,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive)

    def terminal_node(self):
        return True

def ExternalTraceWrapper(wrapped, library, url, method=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance and inspect.ismethod(wrapped):
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)
        
        else:
            _url = url

        if callable(method):
            if instance and inspect.ismethod(wrapped):
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)
        
        else:
            _method = method

        with ExternalTrace(transaction, library, _url, _method):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with ExternalTrace(transaction, library, url, method):
            return wrapped(*args, **kwargs)

    if callable(url) or callable(method):
        return ObjectWrapper(wrapped, None, dynamic_wrapper)

    return ObjectWrapper(wrapped, None, literal_wrapper)

def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library,
            url=url, method=method)

def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper,
            (library, url, method))
