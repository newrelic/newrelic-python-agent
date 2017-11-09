import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)
from tornado.testing import AsyncHTTPTestCase

_default_settings = {
    'feature_flag': set(['tornado.instrumentation.r4']),
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_tornado_r4)',
        default_settings=_default_settings)

_coverage_source = [
    'newrelic.hooks.framework_tornado_r4',
]

code_coverage = code_coverage_fixture(source=_coverage_source)


@pytest.fixture()
def app(request):
    from tornado.ioloop import IOLoop, PollIOLoop

    # Starting with Tornado 5, when available it will use the asyncio event
    # loop. Only the asyncio loop is allowed to be used in this case.

    if IOLoop.configurable_default().__name__ == 'AsyncIOLoop':
        ioloop = IOLoop.configurable_default()
    else:
        ioloop = None
        try:
            ioloop = request.getfixturevalue('ioloop')
        except:
            pass
        finally:
            if ioloop is None:
                ioloop = PollIOLoop.configurable_default()

    class MyTest(AsyncHTTPTestCase):
        def get_new_ioloop(self):
            IOLoop.configure(ioloop)
            return IOLoop.instance()

        def get_app(self):
            from _target_application import make_app
            return make_app()

        def runTest(self, *args, **kwargs):
            pass

    case = MyTest()
    case.setUp()
    yield case
    case.tearDown()
