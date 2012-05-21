from __future__ import with_statement

import functools
import sys
import types
import time
import threading

_context = threading.local()

class InternalTrace(object):

    def __init__(self, name, record=None):
        self.name = name
        self.record = record
        self.start = 0.0

    def __enter__(self):
        if self.record is None and hasattr(_context, 'current'):
            self.record = _context.current.record
        self.start = time.time()
        return self

    def __exit__(self, exc, value, tb):
        duration = max(self.start, time.time()) - self.start
        if self.record:
            self.record(self.name, duration)

class InternalTraceWrapper(object):

    def __init__(self, wrapped, name=None):
        self.wrapped = wrapped
        self.name = name

    def execute(self, wrapped, *args, **kwargs):
        record = None
        if hasattr(_context, 'current'):
            record = _context.current.record

        if record is None:
            return wrapped(*args, **kwargs)

        with InternalTrace(self.name, record):
            return wrapped(*args, **kwargs)

    def __get__(self, instance, klass):
        if instance is None:
            return self

        def wrapper(*args, **kwargs):
            descriptor = self.wrapped.__get__(instance, klass)
            return self.execute(descriptor, *args, **kwargs)

        return wrapper

    def __call__(self, *args, **kwargs):
        return self.execute(self.wrapped, *args, **kwargs)

class InternalTraceContext(object):

    def __init__(self, record):
        self.previous = None
        self.record = record

    def __enter__(self):
        if hasattr(_context, 'current'):
            self.previous = _context.current
        _context.current = self
        return self

    def __exit__(self, exc, value, tb):
        self.current = self.previous
        return

def internal_trace(name=None):
    def decorator(wrapped):
        return InternalTraceWrapper(wrapped, name)
    return decorator

def wrap_internal_trace(module, object_path, name=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            InternalTraceWrapper, (name,))
