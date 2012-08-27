import sys
import unittest

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

from newrelic.api.object_wrapper import (ObjectWrapper, wrap_object,
        callable_name)
        
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

if __name__ == '__main__':
    unittest.main()
