import unittest

import newrelic.api.out_function

_test_result = None
_test_count = 0
_test_phase = None

def _out_function(result):
    global _test_result
    _test_result = result
    global _test_count
    _test_count += 1
    global _test_phase
    _test_phase = '_out_function'
    return result

def _test_function_1(*args, **kwargs):
    global _test_phase
    _test_phase = '_test_function_1'
    return args, kwargs

def _test_function_2(*args, **kwargs):
    global _test_phase
    _test_phase = '_test_function_2'
    return args, kwargs

class _test_class_1:
    def _test_function(self, *args, **kwargs):
        global _test_phase
        _test_phase = '_test_class_1._test_function'
        return args, kwargs

class _test_class_2(object):
    def _test_function(self, *args, **kwargs):
        global _test_phase
        _test_phase = '_test_class_2._test_function'
        return args, kwargs

@newrelic.api.out_function.out_function(_out_function)
def _test_function_3(*args, **kwargs):
    global _test_phase
    _test_phase = '_test_function_3'
    return args, kwargs

class OutFunctionTests(unittest.TestCase):

    def test_wrap_function(self):
        o1 = _test_function_1
        o2 = newrelic.api.out_function.wrap_out_function(__name__,
                '_test_function_1', _out_function)

        self.assertEqual(o1, o2._nr_next_object)
        self.assertEqual(o1, o2._nr_last_object)
        self.assertEqual(o1.__module__, o2.__module__)
        self.assertEqual(o1.__name__, o2.__name__)

        global _test_result
        _test_result = None

        global _test_count
        _test_count = 0

        global _test_phase
        _test_phase = None

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        result = _test_function_1(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_test_result, (args, kwargs))
        self.assertEqual(_test_phase, "_out_function")

        result = _test_function_1(*args, **kwargs)
        result = _test_function_1(*args, **kwargs)

        self.assertEqual(_test_count, 3)

    def test_wrap_old_style_class_method(self):
        o1 = _test_class_1._test_function
        o2 = newrelic.api.out_function.wrap_out_function(__name__,
                '_test_class_1._test_function', _out_function)

        self.assertEqual(o1, o2._nr_next_object)
        self.assertEqual(o1, o2._nr_last_object)
        self.assertEqual(o1.__module__, o2.__module__)
        self.assertEqual(o1.__name__, o2.__name__)

        global _test_result
        _test_result = None

        global _test_count
        _test_count = 0

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        c = _test_class_1()
        result = c._test_function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_test_result, (args, kwargs))

    def test_wrap_new_style_class_method(self):
        o1 = _test_class_2._test_function
        o2 = newrelic.api.out_function.wrap_out_function(__name__,
                '_test_class_2._test_function', _out_function)

        self.assertEqual(o1, o2._nr_next_object)
        self.assertEqual(o1, o2._nr_last_object)
        self.assertEqual(o1.__module__, o2.__module__)
        self.assertEqual(o1.__name__, o2.__name__)

        global _test_result
        _test_result = None

        global _test_count
        _test_count = 0

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        c = _test_class_2()
        result = c._test_function(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_test_result, (args, kwargs))

    def test_decorator_out_function(self):
        global _test_result
        _test_result = None

        global _test_count
        _test_count = 0

        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }

        result = _test_function_3(*args, **kwargs)

        self.assertEqual(result, (args, kwargs))
        self.assertEqual(_test_result, (args, kwargs))

        result = _test_function_3(*args, **kwargs)
        result = _test_function_3(*args, **kwargs)

        self.assertEqual(_test_count, 3)

if __name__ == '__main__':
    unittest.main()
