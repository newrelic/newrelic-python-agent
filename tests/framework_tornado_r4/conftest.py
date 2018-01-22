import pytest
import socket

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

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
    from tornado.testing import AsyncHTTPTestCase
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

    def _bind_unused_port(reuse_port=False):
        from tornado import netutil
        # For tests that use the sock_family fixture, this allows
        # us to make sure that socket is correctly set-up and bound.
        try:
            sock_family = request.getfixturevalue('sock_family')
        except:
            sock_family = socket.AF_INET

        if sock_family is socket.AF_INET:
            address = '127.0.0.1'
        else:
            address = '::1'

        sock = netutil.bind_sockets(None, address=address, family=sock_family,
                                    reuse_port=reuse_port)[0]
        port = sock.getsockname()[1]
        return sock, port

    class MyTest(AsyncHTTPTestCase):
        def get_http_server(self):
            server = super(MyTest, self).get_http_server()

            # add our own port
            sock, port = _bind_unused_port()
            self._port = port

            server.add_sockets([sock])

            # prevent any other sockets from getting added
            server.add_sockets = lambda *args, **kwargs: None
            return server

        def get_http_port(self):
            return self._port

        def get_new_ioloop(self):
            IOLoop.configure(ioloop)
            return IOLoop()

        def get_app(self):
            from _target_application import make_app
            return make_app()

        def get_url(self, path):
            # Allow for testing ipv6 by using localhost instead of 127.0.0.1
            return '%s://localhost:%s%s' % (self.get_protocol(),
                    self.get_http_port(), path)

        def runTest(self, *args, **kwargs):
            pass

    case = MyTest()
    case.setUp()
    yield case
    case.tearDown()
