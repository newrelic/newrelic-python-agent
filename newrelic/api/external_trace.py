import os
import sys
import types
import inspect
import time
import collections

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

ExternalNode = collections.namedtuple('ExternalNode',
        ['library', 'url', 'children', 'start_time', 'end_time'])

class ExternalTrace(object):

    def __init__(self, transaction, library, url):
        self._transaction = transaction

        self._library = library
        self._url = url

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction.active:
            return

        self._enabled = True

        self._start_time = time.time()

        self._transaction._node_stack.append(self)

        return self

    def __exit__(self, exc, value, tb):
        if not self._enabled:
            return

        self._end_time = time.time()

        node = self._transaction._node_stack.pop()
        assert(node == self)

        parent = self._transaction._node_stack[-1]

        parent._children.append(ExternalNode(library=self._library,
                url=self._url, children=self._children,
                start_time=self._start_time, end_time=self._end_time))

        self._children = []

if _agent_mode not in ('julunggul',):
    import _newrelic
    ExternalTrace = _newrelic.ExternalTrace

class ExternalTraceWrapper(object):

    def __init__(self, wrapped, library, url):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_library = library
        self._nr_url = url

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_library,
                              self._nr_url)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction or not transaction.active:
            return self._nr_next_object(*args, **kwargs)

        if not isinstance(self._nr_url, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                url = self._nr_url(*((self._nr_instance,)+args), **kwargs)
            else:
                url = self._nr_url(*args, **kwargs)
        else:
            url = self._nr_url

        try:
            success = True
            manager = ExternalTrace(transaction, self._nr_library, url)
            manager.__enter__()
            try:
                return self._nr_next_object(*args, **kwargs)
            except:
                success = False
                if not manager.__exit__(*sys.exc_info()):
                    raise
        finally:
            if success:
                manager.__exit__(None, None, None)

def external_trace(library, url):
    def decorator(wrapped):
        return ExternalTraceWrapper(wrapped, library, url)
    return decorator

def wrap_external_trace(module, object_path, library, url):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            ExternalTraceWrapper, (library, url))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    ExternalTraceWrapper = _newrelic.ExternalTraceWrapper
    external_trace = _newrelic.external_trace
    wrap_external_trace = _newrelic.wrap_external_trace
