import logging
import unittest
import types

import newrelic.api.settings
import newrelic.api.object_wrapper

_logger = logging.getLogger('newrelic')

settings = newrelic.api.settings.settings()

settings.host = 'staging-collector.newrelic.com'
settings.license_key = '84325f47e9dec80613e262be4236088a9983d501'

settings.app_name = 'Python Unit Tests'

settings.log_file = '%s.log' % __file__
settings.log_level = logging.DEBUG

settings.transaction_tracer.transaction_threshold = 0
settings.transaction_tracer.stack_trace_threshold = 0

settings.shutdown_timeout = 10.0

settings.debug.log_data_collector_calls = True
settings.debug.log_data_collector_payloads = True

_function_args = None

def _function(*args, **kwargs):
    return (args, kwargs)

class _wrapper(object):
   def __init__(self, wrapped):
       self.wrapped = wrapped
   def __get__(self, obj, objtype=None):
       return types.MethodType(self, obj, objtype)
   def __call__(self, *args, **kwargs):
       global _function_args
       _function_args = (args, kwargs)
       return self.wrapped(*args, **kwargs)

class ApplicationTests(unittest.TestCase):

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

    def test_wrap_object(self):
        newrelic.api.object_wrapper.wrap_object(
                __name__, '_function', _wrapper)
        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }
        result = _function(*args, **kwargs)
        self.assertEqual(result, (args, kwargs))

if __name__ == '__main__':
    unittest.main()
