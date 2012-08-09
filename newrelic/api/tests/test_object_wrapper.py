import sys
import unittest

from newrelic.api.object_wrapper import ObjectWrapper, wrap_object
        
def Wrapper(wrapped):

    def wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

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

if __name__ == '__main__':
    unittest.main()
