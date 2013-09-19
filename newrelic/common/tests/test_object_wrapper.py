import sys
import unittest
import functools

from collections import namedtuple

import newrelic.packages.six as six

from newrelic.common.object_wrapper import ObjectWrapper

def Wrapper(wrapped):

    def wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

class ObjectWrapperTests(unittest.TestCase):

    def test_attribute_access(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy = ObjectWrapper(function, None, wrapper)

        self.assertEqual(proxy._nr_next_object, function)
        self.assertEqual(proxy._nr_last_object, function)
        self.assertEqual(proxy._nr_instance, None)
        self.assertEqual(proxy._nr_wrapper, wrapper)

    def test_attribute_update(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy = ObjectWrapper(function, None, wrapper)

        proxy._nr_attribute = 1

        self.assertEqual(proxy._nr_attribute, 1)

        # A _self__attribute will actually exist because of the
        # name remapping which occurs to align old conventions
        # for naming in ObjectWrapper with that of ObjectProxy in
        # wrapt module. The attribute should exist only on the
        # wrapper and not the wrapped function.

        self.assertEqual(proxy._self_attribute, 1)
        self.assertFalse(hasattr(function, '_self_attribute'))

        del proxy._nr_attribute
        self.assertFalse(hasattr(proxy, '_nr_attribute'))
        self.assertFalse(hasattr(proxy, '_self_attribute'))

    def test_nested_wrappers(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy1 = ObjectWrapper(function, None, wrapper)
        proxy2 = ObjectWrapper(proxy1, None, wrapper)

        self.assertEqual(proxy2._nr_next_object, proxy1)
        self.assertEqual(proxy2._nr_last_object, function)

    def test_bound_wrapper(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy1 = ObjectWrapper(function, None, wrapper)

        obj = object()

        proxy2 = proxy1.__get__(obj, type(obj))

        self.assertEqual(proxy2._nr_next_object.__func__, function)
        self.assertEqual(proxy2._nr_last_object.__func__, function)
        self.assertEqual(proxy2._nr_instance, obj)

if __name__ == '__main__':
    unittest.main()
