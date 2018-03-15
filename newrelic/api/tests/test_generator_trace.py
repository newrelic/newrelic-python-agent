import pytest
import sys
import time
import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.generator_trace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()


@newrelic.api.generator_trace.generator_trace()
def _test_function_1():
    for i in range(4):
        time.sleep(0.5)
        yield time.time()


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    @pytest.mark.xfail(sys.version_info >= (3, 7), strict=True,
            reason='PYTHON-2700')
    def test_function_trace_decorator(self):
        environ = {"REQUEST_URI": "/generator_trace_decorator"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            result = _test_function_1()
            for item in result:
                pass
            time.sleep(0.1)


if __name__ == '__main__':
    unittest.main()
