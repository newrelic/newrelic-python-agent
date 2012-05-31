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

class FunctionProfileWrapper(ObjectWrapper):

    def __init__(self, wrapped, filename, delay=1.0, checkpoint=30):
        self._nr_instance = None
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_filename = filename % { 'pid': os.getpid() }
        self._nr_delay = delay
        self._nr_checkpoint = checkpoint

        self._nr_lock = threading.Lock()
        self._nr_profile = cProfile.Profile()

        self._nr_last = time.time() - delay

        self._nr_active = False
        self._nr_count = 0

    def _nr_invoke(self, wrapped, *args, **kwargs):
        with self._nr_lock:
            if self._nr_active:
                return wrapped(*args, **kwargs)

            if time.time() - self._nr_last < self._nr_delay:
                return wrapped(*args, **kwargs)

            self._nr_active = True
            self._nr_count += 1

        try:
            with FunctionProfile(self._nr_profile):
                result = wrapped(*args, **kwargs)

            if (self._nr_count % self._nr_checkpoint) == 0:
                self._nr_profile.dump_stats(self._nr_filename)

            return result

        finally:
            self._nr_last = time.time()
            self._nr_active = False

    def __get__(self, instance, klass):
        if instance is None:
            return self

        @functools.wraps(self._nr_next_object)
        def wrapper(*args, **kwargs):
            descriptor = self._nr_next_object.__get__(instance, klass)
            return self._nr_invoke(descriptor, *args, **kwargs)

        return wrapper

    def __call__(self, *args, **kwargs):
        return self._nr_invoke(_nr_next_object, *args, **kwargs)

def function_profile(filename, delay=1.0, checkpoint=30):
    def decorator(wrapped):
        return FunctionProfileWrapper(wrapped, filename, delay, checkpoint)
    return decorator

def wrap_function_profile(module, object_path, filename, delay=1.0,
        checkpoint=30):
    wrap_object(module, object_path, FunctionProfileWrapper,
            (filename, delay, checkpoint))
