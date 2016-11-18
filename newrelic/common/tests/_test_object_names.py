import functools

from collections import namedtuple


def _function1(self): pass

def _function_a(a): pass

_partial_function1 = functools.partial(_function_a, a=1)

class _class1():

    def _function1(self): pass

    @classmethod
    def _function2(cls): pass

    @staticmethod
    def _function3(): pass

class _class2(object):

    def _function1(self): pass

    @classmethod
    def _function2(cls): pass

    @staticmethod
    def _function3(): pass

_class3 = namedtuple('_class3', 'a')

def _decorator1(wrapped):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        return wrapped(*args, **kwargs)
    return wrapper

class _decorator2(object):

    def __init__(self, wrapped):
        self._nr_wrapped = wrapped

        try:
            object.__setattr__(self, '__qualname__', wrapped.__qualname__)
        except AttributeError:
            pass

        try:
            object.__setattr__(self, '__name__', wrapped.__name__)
        except AttributeError:
            pass

    @property
    def __module__(self):
        return self._self_wrapped.__module__

    def __getattr__(self, name):
        return getattr(self._nr_wrapped, name)

    def __get__(self, instance, owner):
        descriptor = self._nr_wrapped.__get__(instance, owner)
        return self.__class__(descriptor)

    def __call__(self, *args, **kwargs):
        return self._nr_wrapped(*args, **kwargs)

    def decorator(self, *args, **kwargs):
        pass

@_decorator1
def _function2(self): pass

@_decorator2
def _function3(self): pass

class _class4(object):

    @_decorator1
    def _function1(self): pass

    @_decorator2
    def _function2(self): pass

class _class5(object):
    class _class6(object):
        def _function1(self): pass

class _class7(_class1):
    def _function4(self): pass

class _class8(_class2):
    def _function4(self): pass

def _module_fqdn(path, name=None):
  name = name or __name__
  return '%s:%s' % (name, path)
