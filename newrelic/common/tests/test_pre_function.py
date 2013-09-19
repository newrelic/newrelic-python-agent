import unittest

from newrelic.common.object_wrapper import (pre_function, wrap_pre_function)

def _test_wrap_function(*args, **kwargs):
    _test_wrap_function.last = '_test_wrap_function'
    return args, kwargs

class _TestClassWrapMethod(object):
    def function(self, *args, **kwargs):
        return args, kwargs

class PreFunctionTests(unittest.TestCase):

    def test_wrap_function(self):
        def _pre_function(*args, **kwargs):
            _test_wrap_function.last = '_pre_function'
            _pre_function.params = (args, kwargs)
            return args, kwargs

        wrap_pre_function(__name__, '_test_wrap_function', _pre_function)

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        result = _test_wrap_function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, (args, kwargs))

        self.assertEqual(_test_wrap_function.last, '_test_wrap_function')

    def test_wrap_instance_method(self):
        def _pre_function(*args, **kwargs):
            _pre_function.params = (args, kwargs)
            return args, kwargs

        wrap_pre_function(__name__,
                '_TestClassWrapMethod.function', _pre_function)

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        c = _TestClassWrapMethod()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((c,)+args, kwargs))

        result = _TestClassWrapMethod.function(c, *args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((c,)+args, kwargs))

    def test_decorator_function(self):
        def _pre_function(*args, **kwargs):
            _pre_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        @pre_function(_pre_function)
        def function(*args, **kwargs):
            return args, kwargs

        result = function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, (args, kwargs))

    def test_decorator_instancemethod(self):
        def _pre_function(*args, **kwargs):
            _pre_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        class Class(object):
            @pre_function(_pre_function)
            def function(self, *args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((c,)+args, kwargs))

        result = Class.function(c, *args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((c,)+args, kwargs))

    def test_decorator_classmethod(self):
        def _pre_function(*args, **kwargs):
            _pre_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        class Class(object):
            @pre_function(_pre_function)
            @classmethod
            def function(cls, *args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((Class,)+args, kwargs))

        result = Class.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, ((Class,)+args, kwargs))

    def test_decorator_staticmethod(self):
        def _pre_function(*args, **kwargs):
            _pre_function.params = (args, kwargs)
            return args, kwargs

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        class Class(object):
            @pre_function(_pre_function)
            @staticmethod
            def function(*args, **kwargs):
                return args, kwargs

        c = Class()

        result = c.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, (args, kwargs))

        result = Class.function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_pre_function.params, (args, kwargs))

if __name__ == '__main__':
    unittest.main()
