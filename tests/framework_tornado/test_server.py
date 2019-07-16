import pytest
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings, function_not_called,
        validate_transaction_event_attributes,
        validate_transaction_errors,
        override_application_settings)
from testing_support.validators.validate_transaction_count import (
        validate_transaction_count)


@pytest.mark.parametrize('uri,name,metrics', (
    ('/native-simple', 'tornado.routing:_RoutingDelegate', None),
    ('/simple', 'tornado.routing:_RoutingDelegate', None),
    ('/call-simple', 'tornado.routing:_RoutingDelegate', None),
    ('/coro', 'tornado.routing:_RoutingDelegate', None),
    ('/fake-coro', 'tornado.routing:_RoutingDelegate', None),
    ('/coro-throw', 'tornado.routing:_RoutingDelegate', None),
    ('/init', 'tornado.routing:_RoutingDelegate', None),
    ('/multi-trace',
            'tornado.routing:_RoutingDelegate', [('Function/trace', 2)]),
))
@override_application_settings({'attributes.include': ['request.*']})
def test_server(app, uri, name, metrics):
    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version
    metrics = metrics or []
    metrics.append((FRAMEWORK_METRIC, 1))

    host = '127.0.0.1:' + str(app.get_http_port())

    @validate_transaction_metrics(
        name,
        rollup_metrics=metrics,
    )
    @validate_transaction_event_attributes(
        required_params={
            'agent': ('response.headers.contentType',),
            'user': (), 'intrinsic': ()},
        exact_attrs={
            'agent': {'request.headers.contentType': '1234',
                'request.headers.host': host,
                'request.method': 'GET',
                'request.uri': uri,
                'response.status': '200'},
            'user': {},
            'intrinsic': {'port': app.get_http_port()},
        },
    )
    def _test():
        response = app.fetch(uri, headers=(('Content-Type', '1234'),))
        assert response.code == 200

    _test()


@pytest.mark.parametrize('uri,name,metrics', (
    ('/native-simple', 'tornado.routing:_RoutingDelegate', None),
    ('/simple', 'tornado.routing:_RoutingDelegate', None),
    ('/call-simple', 'tornado.routing:_RoutingDelegate', None),
    ('/coro', 'tornado.routing:_RoutingDelegate', None),
    ('/fake-coro', 'tornado.routing:_RoutingDelegate', None),
    ('/coro-throw', 'tornado.routing:_RoutingDelegate', None),
    ('/init', 'tornado.routing:_RoutingDelegate', None),
    ('/multi-trace',
            'tornado.routing:_RoutingDelegate', [('Function/trace', 2)]),
))
def test_concurrent_inbound_requests(app, uri, name, metrics):
    from tornado import gen

    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version
    metrics = metrics or []
    metrics.append((FRAMEWORK_METRIC, 1))

    @validate_transaction_count(2)
    @validate_transaction_metrics(
        name,
        rollup_metrics=metrics,
    )
    def _test():
        url = app.get_url(uri)
        coros = (app.http_client.fetch(url) for _ in range(2))
        responses = app.io_loop.run_sync(lambda: gen.multi(coros))

        for response in responses:
            assert response.code == 200

    _test()


@validate_transaction_errors(['builtins:ValueError'])
def test_exceptions_are_recorded(app):
    response = app.fetch('/crash')
    assert response.code == 500


@override_generic_settings(global_settings(), {
    'enabled': False,
})
@function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
def test_nr_disabled(app):
    response = app.fetch('/simple')
    assert response.code == 200


def test_web_socket(app):
    import asyncio
    from tornado.websocket import websocket_connect

    url = app.get_url('/web-socket').replace('http', 'ws')

    @asyncio.coroutine
    def _connect():
        conn = yield from websocket_connect(url)
        return conn

    @validate_transaction_metrics(
        "tornado.routing:_RoutingDelegate",
    )
    def connect():
        return app.io_loop.run_sync(_connect)

    @function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def call(call):
        @asyncio.coroutine
        def _call():
            yield from conn.write_message("test")
            resp = yield from conn.read_message()
            assert resp == "hello test"
        app.io_loop.run_sync(_call)

    conn = connect()
    call(conn)
    conn.close()
