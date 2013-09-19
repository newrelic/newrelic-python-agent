import unittest

from newrelic.common.object_wrapper import (in_function, wrap_in_function)

def _test_wrap_function(*args, **kwargs):
    _test_wrap_function.last = '_test_wrap_function'
    return args, kwargs

class _TestClassWrapMethod(object):
    def function(self, *args, **kwargs):
        return args, kwargs

class InFunctionTests(unittest.TestCase):

    def test_wrap_function(self):
        def _in_function(*args, **kwargs):
            args = tuple(reversed(args))
            _test_wrap_function.last = '_in_function'
            _in_function.params = (args, kwargs)
            return args, kwargs

        wrap_in_function(__name__, '_test_wrap_function', _in_function)

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        result = _test_wrap_function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, (rargs, kwargs))

        self.assertEqual(_test_wrap_function.last, '_test_wrap_function')

    def test_wrap_instance_method(self):
        def _in_function(*args, **kwargs):
            args = (args[0],)+tuple(reversed(args[1:]))
            _in_function.params = (args, kwargs)
            return args, kwargs

        wrap_in_function(__name__,
                '_TestClassWrapMethod.function', _in_function)

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        c = _TestClassWrapMethod()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((c,)+rargs, kwargs))

        result = _TestClassWrapMethod.function(c, *args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((c,)+rargs, kwargs))

    def test_decorator_function(self):
        def _in_function(*args, **kwargs):
            args = tuple(reversed(args))
            _in_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        @in_function(_in_function)
        def function(*args, **kwargs):
            return args, kwargs

        result = function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, (rargs, kwargs))

    def test_decorator_instancemethod(self):
        def _in_function(*args, **kwargs):
            args = (args[0],)+tuple(reversed(args[1:]))
            _in_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        class Class(object):
            @in_function(_in_function)
            def function(self, *args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((c,)+rargs, kwargs))

        result = Class.function(c, *args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((c,)+rargs, kwargs))

    def test_decorator_classmethod(self):
        def _in_function(*args, **kwargs):
            args = (args[0],)+tuple(reversed(args[1:]))
            _in_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        class Class(object):
            @in_function(_in_function)
            @classmethod
            def function(cls, *args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((Class,)+rargs, kwargs))

        result = Class.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, ((Class,)+rargs, kwargs))

    def test_decorator_staticmethod(self):
        def _in_function(*args, **kwargs):
            args = tuple(reversed(args))
            _in_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        rargs = tuple(reversed(args))

        class Class(object):
            @in_function(_in_function)
            @staticmethod
            def function(*args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, (rargs, kwargs))

        result = Class.function(*args, **kwargs)

        self.assertEqual(result, (rargs, kwargs))
        self.assertEqual(_in_function.params, (rargs, kwargs))

if __name__ == '__main__':
    unittest.main()
