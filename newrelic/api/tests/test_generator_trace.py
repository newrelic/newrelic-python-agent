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
        time.sleep(0.1)
        yield time.time()


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_function_trace_decorator(self):
        environ = {"REQUEST_URI": "/generator_trace_decorator"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        with transaction:
            result = _test_function_1()
            prev_t = 0
            for t in result:
                assert t > prev_t, "Time has gone backwards!"
                prev_t = t

        assert transaction.total_time >= 0.4
        assert len(transaction.current_span.children) == 6


if __name__ == '__main__':
    unittest.main()
