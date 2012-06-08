from __future__ import with_statement

import cProfile
import functools
import os
import threading
import time

from newrelic.api.object_wrapper import ObjectWrapper, wrap_object

class FunctionProfile(object):

    def __init__(self, profile):
        self.profile = profile

    def __enter__(self):
        self.profile.enable()
        return self

    def __exit__(self, exc, value, tb):
        self.profile.disable()
        pass

class FunctionProfileContext(object):

    def __init__(self, filename, delay=1.0, checkpoint=30):
        self.filename = filename % { 'pid': os.getpid() }
        self.delay = delay
        self.checkpoint = checkpoint

        self.lock = threading.Lock()
        self.profile = cProfile.Profile()

        self.last = time.time() - delay

        self.active = False
        self.count = 0

    def invoke(self, wrapped, instance, *args, **kwargs):
        with self.lock:
            if self.active:
                return wrapped(*args, **kwargs)

            if time.time() - self.last < self.delay:
                return wrapped(*args, **kwargs)

            self.active = True
            self.count += 1

        try:
            with FunctionProfile(self.profile):
                result = wrapped(*args, **kwargs)

            if (self.count % self.checkpoint) == 0:
                self.profile.dump_stats(self.filename)

            return result

        finally:
            self.last = time.time()
            self.active = False

class _FunctionProfileWrapper(object):

    def __init__(self, wrapped, instance, context):
        self._nr_wrapped = wrapped
        self._nr_instance = instance
        self._nr_context = context

    def __getattr__(self, name):
        return getattr(self._nr_wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_wrapped.__get__(instance, klass)
        return self.__class__(descriptor, instance, self._nr_context)

    def __call__(self, *args, **kwargs):
        return self._nr_context.invoke(self._nr_wrapped,
            self._nr_instance, *args, **kwargs)

def FunctionProfileWrapper(wrapped, filename, delay=1.0, checkpoint=30):
    context = FunctionProfileContext(filename, delay, checkpoint)
    return _FunctionProfileWrapper(wrapped, None, context)

def function_profile(filename, delay=1.0, checkpoint=30):
    def decorator(wrapped):
        return FunctionProfileWrapper(wrapped, filename, delay, checkpoint)
    return decorator

def wrap_function_profile(module, object_path, filename, delay=1.0,
        checkpoint=30):
    wrap_object(module, object_path, FunctionProfileWrapper,
            (filename, delay, checkpoint))
