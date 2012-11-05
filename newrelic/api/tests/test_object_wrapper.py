import sys
import unittest
import functools

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

from newrelic.api.object_wrapper import (ObjectWrapper, wrap_object,
        callable_name, WRAPPER_ASSIGNMENTS)
        
def Wrapper(wrapped):

    def wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

def _function1(self): pass

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

        for attr in WRAPPER_ASSIGNMENTS:
            try:
                value = getattr(wrapped, attr)
            except AttributeError:
                pass
            else:
                object.__setattr__(self, attr, value)

    def __getattr__(self, name):
        return getattr(self._nr_wrapped, name)

    def __get__(self, instance, owner):
        if instance is None:
            return self
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

def _module_fqdn(path, name=None):
  name = name or __name__
  return '%s:%s' % (name, path)

CALLABLES = [
  (_function1, _module_fqdn('_function1')),

  (_class1, _module_fqdn('_class1')),
  (_class1(), _module_fqdn('_class1')),

  (_class1._function1, _module_fqdn('_class1._function1')),
  (_class1()._function1, _module_fqdn('_class1._function1')),

  (_class1._function2, _module_fqdn('_class1._function2')),
  (_class1()._function2, _module_fqdn('_class1._function2')),

  # Not possible to get the class corresponding to a static method.
  (_class1._function3, _module_fqdn('_function3')),
  (_class1()._function3, _module_fqdn('_function3')),

  (_class2, _module_fqdn('_class2')),
  (_class2(), _module_fqdn('_class2')),

  (_class2._function1, _module_fqdn('_class2._function1')),
  (_class2()._function1, _module_fqdn('_class2._function1')),

  (_class2._function2, _module_fqdn('_class2._function2')),
  (_class2()._function2, _module_fqdn('_class2._function2')),

  # Not possible to get the class corresponding to a static method.
  (_class2._function3, _module_fqdn('_function3')),
  (_class2()._function3, _module_fqdn('_function3')),

  (_class3, _module_fqdn('_class3')),
  (_class3(1), _module_fqdn('_class3')),

  (_class3._make, _module_fqdn('_class3._make')),
  (_class3(1)._make, _module_fqdn('_class3._make')),

  (_class3._asdict, _module_fqdn('_class3._asdict')),
  (_class3(1)._asdict, _module_fqdn('_class3._asdict')),

  (_function2, _module_fqdn('_function2')),
  (_function3, _module_fqdn('_function3')),

  (_class4._function1, _module_fqdn('_class4._function1')),
  (_class4()._function1, _module_fqdn('_class4._function1')),

  # Not possible to get the class where decorator is a class object.
  (_class4._function2, _module_fqdn('_function2')),
  (_class4()._function2, _module_fqdn('_function2')),
]

class ObjectWrapperTests(unittest.TestCase):

    def test_object_wrapper(self):

        def _test_function_1(*args, **kwargs):
            return args, kwargs

        o1 = _test_function_1
        o2 = Wrapper(_test_function_1)

        self.assertEqual(o1, o2._nr_next_object)
        self.assertEqual(o1, o2._nr_last_object)
        self.assertEqual(o1.__module__, o2.__module__)
        self.assertEqual(o1.__name__, o2.__name__)

        o1.xxx = object()
        self.assertEqual(o1.xxx, o2.xxx)

        o2.xxx = object()
        self.assertEqual(o1.xxx, o2.xxx)

        args = (1, 2, 3)
        kwargs = { "a": "a", "b": "b", "c": "c" }

        self.assertEqual((args, kwargs), o2(*args, **kwargs))

        # Proxying of __dir__() was only added in Python 2.6.

        if sys.version_info[:2] >= (2, 6):
            self.assertEqual(dir(o1), dir(o2))

    def test_callable_name(self):
        for callable, name in CALLABLES:
            self.assertEqual(callable_name(callable), name)

    def test_comparison(self):
        def _test_function_1(*args, **kwargs):
            return args, kwargs
        def _test_function_2(*args, **kwargs):
            return args, kwargs

        o1a = _test_function_1
        o1b = Wrapper(_test_function_1)
        o1c = Wrapper(_test_function_1)

        o2a = _test_function_2
        o2b = Wrapper(_test_function_2)
        o2c = Wrapper(_test_function_2)

        self.assertEqual(o1a, o1b)
        self.assertEqual(o1b, o1a)
        self.assertEqual(o1b, o1c)
        self.assertEqual(o1c, o1b)

        self.assertEqual(hash(o1a), hash(o1b))
        self.assertEqual(hash(o1b), hash(o1c))

        map = { o1a: True }

        self.assertTrue(map[o1b])
        self.assertTrue(map[o1c])

        self.assertNotEqual(o1b, o2b)
        self.assertNotEqual(o2b, o1b)

    def test_display(self):
        def _test_function_1(*args, **kwargs):
            return args, kwargs

        o1a = _test_function_1
        o1b = Wrapper(_test_function_1)

        s = '<ObjectWrapper for %s>' % str(o1a)

        self.assertEqual(s, str(o1b))
        self.assertEqual(s, repr(o1b))
        self.assertEqual(s, unicode(o1b))

if __name__ == '__main__':
    unittest.main()
