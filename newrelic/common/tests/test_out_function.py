import unittest

from newrelic.common.object_wrapper import (out_function, wrap_out_function)

def _test_wrap_function(value):
    _test_wrap_function.last = '_test_wrap_function'
    return value

class _TestClassWrapMethod(object):
    def function(self, value):
        return value

class OutFunctionTests(unittest.TestCase):

    def test_wrap_function(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _test_wrap_function.last = '_out_function'
            _out_function.result = result
            return result

        wrap_out_function(__name__, '_test_wrap_function', _out_function)

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        result = _test_wrap_function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

        self.assertEqual(_test_wrap_function.last, '_out_function')

    def test_wrap_instance_method(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _out_function.result = result
            return result

        wrap_out_function(__name__,
                '_TestClassWrapMethod.function', _out_function)

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        c = _TestClassWrapMethod()

        result = c.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

        result = _TestClassWrapMethod.function(c, value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

    def test_decorator_function(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _out_function.result = result
            return result

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        @out_function(_out_function)
        def function(value):
            return value

        result = function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

    def test_decorator_instancemethod(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _out_function.result = result
            return result

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        class Class(object):
            @out_function(_out_function)
            def function(self, value):
                return value

        c = Class()

        result = c.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

        result = Class.function(c, value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

    def test_decorator_classmethod(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _out_function.result = result
            return result

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        class Class(object):
            @out_function(_out_function)
            @classmethod
            def function(cls, value):
                return value

        c = Class()

        result = c.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

        result = Class.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

    def test_decorator_staticmethod(self):
        def _out_function(result):
            result = tuple(reversed(result))
            _out_function.result = result
            return result

        value = (1, 2, 3)
        rvalue = tuple(reversed(value))

        class Class(object):
            @out_function(_out_function)
            @staticmethod
            def function(value):
                return value

        c = Class()

        result = c.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

        result = Class.function(value)

        self.assertEqual(result, rvalue)
        self.assertEqual(_out_function.result, rvalue)

if __name__ == '__main__':
    unittest.main()
