import sys
import unittest
import functools

from collections import namedtuple

import newrelic.packages.six as six

from newrelic.common.object_wrapper import ObjectWrapper, function_wrapper
from newrelic.common.object_names import callable_name, object_context

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

        self.assertTrue(proxy2._self_parent is proxy1)

        self.assertEqual(proxy2._nr_next_object.__func__, function)
        self.assertEqual(proxy2._nr_last_object.__func__, function)
        self.assertEqual(proxy2._nr_instance, obj)

    def test_rebound_wrapper(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy1 = ObjectWrapper(function, None, wrapper)

        self.assertEqual(proxy1._self_binding, 'function')

        obj = object()

        proxy2 = proxy1.__get__(None, type(None))

        self.assertTrue(proxy2._self_parent is proxy1)
        self.assertTrue(proxy2._self_instance is None)
        self.assertEqual(proxy2._self_binding, 'function')

        if six.PY2:
            # No such thing as unbound function in Python 3.
            self.assertEqual(proxy2._nr_next_object.__func__, function)
            self.assertEqual(proxy2._nr_last_object.__func__, function)

        self.assertEqual(proxy2._nr_instance, None)

        proxy3 = proxy2.__get__(obj, type(obj))

        self.assertTrue(proxy3._self_parent is proxy1)

        self.assertFalse(proxy2 is proxy3)

        self.assertEqual(proxy3._nr_next_object.__func__, function)
        self.assertEqual(proxy3._nr_last_object.__func__, function)
        self.assertEqual(proxy3._nr_instance, obj)

    def test_override_getattr(self):

        def function():
            pass

        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        proxy1 = ObjectWrapper(function, None, wrapper)

        function.attribute = 1

        self.assertEqual(proxy1.attribute, 1)

        class CustomProxy1(ObjectWrapper):
            def __getattr__(self, name):
                return 2*super(CustomProxy1, self).__getattr__(name)

        proxy2 = CustomProxy1(function, None, wrapper)

        self.assertEqual(proxy2.attribute, 2)

        proxy1._nr_attribute = 1

        self.assertEqual(proxy1._nr_attribute, 1)

        self.assertFalse(hasattr(function, '_nr_attribute'))
        self.assertFalse(hasattr(function, '_self_attribute'))

        proxy2._nr_attribute = 2

        self.assertEqual(proxy2._nr_attribute, 4)

        self.assertFalse(hasattr(function, '_nr_attribute'))
        self.assertFalse(hasattr(function, '_self_attribute'))

        class CustomProxy2a(ObjectWrapper):
            def __init__(self, wrapped, instance, wrapper):
                super(CustomProxy2a, self).__init__(wrapped, None, None)
        class CustomProxy2b(CustomProxy2a):
            def __getattr__(self, name):
                return 2*super(CustomProxy2b, self).__getattr__(name)

        proxy3 = CustomProxy2b(function, None, wrapper)

        self.assertEqual(proxy3.attribute, 2)

        proxy1._nr_attribute = 1

        self.assertEqual(proxy1._nr_attribute, 1)

        self.assertFalse(hasattr(function, '_nr_attribute'))
        self.assertFalse(hasattr(function, '_self_attribute'))

        proxy3._nr_attribute = 2

        self.assertEqual(proxy3._nr_attribute, 4)

        self.assertFalse(hasattr(function, '_nr_attribute'))
        self.assertFalse(hasattr(function, '_self_attribute'))

@function_wrapper
def wrapper(wrapped, instance, args, kwargs):
    return wrapped(*args, **kwargs)

@wrapper
def _function1():
    pass

@wrapper
class Class1(object):

    @wrapper
    def function(self):
        pass

def _module_fqdn(path, name=None):
  name = name or __name__
  return '%s:%s' % (name, path)

class TestCallableName(unittest.TestCase):

    def test_decorated_function(self):
        self.assertEqual(callable_name(_function1),
                _module_fqdn(_function1.__name__))

        details1 = object_context(_function1)
        details2 = object_context(_function1)

        self.assertTrue(details1 is details2)

    def test_decorated_class(self):
        self.assertEqual(callable_name(Class1),
                _module_fqdn(Class1.__name__))

        details1 = object_context(Class1)
        details2 = object_context(Class1)

        self.assertTrue(details1 is details2)

    def test_decorated_instancemethod(self):
        self.assertEqual(callable_name(Class1.function),
                _module_fqdn(Class1.__name__+'.'+Class1.function.__name__))

        if six.PY3:
            self.assertEqual(callable_name(Class1.function),
                    _module_fqdn(Class1.function.__qualname__))

        details1 = object_context(Class1.function)
        details2 = object_context(Class1.function)

        self.assertTrue(details1 is details2)


def delegating_wrapper(function):
    @function_wrapper
    def _wrapper(wrapped, instance, args, kwargs):
        if instance:
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)
        return wrapped(*args, **kwargs)
    return _wrapper

class TestInstanceChecks(unittest.TestCase):

    def test_function(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(*args, **kwargs):
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        @delegating_wrapper(_function)
        def function(*args, **kwargs):
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)
            return args, kwargs

        result = function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_instancemethod_via_instance(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(instance, *args, **kwargs):
            self.assertEqual(instance, _instance)
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            def function(_self, *args, **kwargs):
                self.assertEqual(_self, _instance)
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = _instance.function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_instancemethod_via_class(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(instance, *args, **kwargs):
            self.assertEqual(instance, _instance)
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            def function(_self, *args, **kwargs):
                self.assertEqual(_self, _instance)
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = Class.function(_instance, *_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_classmethod_instance(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(instance, *args, **kwargs):
            self.assertEqual(instance, Class)
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            @classmethod
            def function(cls, *args, **kwargs):
                self.assertEqual(cls, Class)
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = _instance.function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_classmethod_via_class(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(instance, *args, **kwargs):
            self.assertEqual(instance, Class)
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            @classmethod
            def function(cls, *args, **kwargs):
                self.assertEqual(cls, Class)
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = Class.function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_staticmethod_instance(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(*args, **kwargs):
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            @staticmethod
            def function(*args, **kwargs):
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = _instance.function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

    def test_staticmethod_via_class(self):

        _args = (1, 2)
        _kwargs = { "one": 1, "two": 2 }

        def _function(*args, **kwargs):
            self.assertEqual(args, _args)
            self.assertEqual(kwargs, _kwargs)

        class Class(object):

            @delegating_wrapper(_function)
            @staticmethod
            def function(*args, **kwargs):
                self.assertEqual(args, _args)
                self.assertEqual(kwargs, _kwargs)
                return args, kwargs

        _instance = Class()

        result = Class.function(*_args, **_kwargs)

        self.assertEqual(result, (_args, _kwargs))

if __name__ == '__main__':
    unittest.main()
