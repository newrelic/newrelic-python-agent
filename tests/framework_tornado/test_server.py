import pytest
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings, function_not_called,
        validate_transaction_event_attributes)
from testing_support.validators.validate_transaction_count import (
        validate_transaction_count)


@pytest.mark.parametrize('uri,name', (
    ('/native-simple', 'tornado.routing:_RoutingDelegate'),
    ('/simple', 'tornado.routing:_RoutingDelegate'),
    ('/call-simple', 'tornado.routing:_RoutingDelegate'),
    ('/coro', 'tornado.routing:_RoutingDelegate'),
    ('/fake-coro', 'tornado.routing:_RoutingDelegate'),
    ('/coro-throw', 'tornado.routing:_RoutingDelegate'),
    ('/init', 'tornado.routing:_RoutingDelegate'),
))
def test_server(app, uri, name):
    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version

    @validate_transaction_metrics(
        name,
        rollup_metrics=((FRAMEWORK_METRIC, 1),),
    )
    @validate_transaction_event_attributes(
        required_params={'agent': (), 'user': (), 'intrinsic': ('port',)},
    )
    def _test():
        response = app.fetch(uri)
        assert response.code == 200

    _test()


@pytest.mark.parametrize('uri,name', (
    ('/native-simple', 'tornado.routing:_RoutingDelegate'),
    ('/simple', 'tornado.routing:_RoutingDelegate'),
    ('/call-simple', 'tornado.routing:_RoutingDelegate'),
    ('/coro', 'tornado.routing:_RoutingDelegate'),
    ('/fake-coro', 'tornado.routing:_RoutingDelegate'),
    ('/coro-throw', 'tornado.routing:_RoutingDelegate'),
    ('/init', 'tornado.routing:_RoutingDelegate'),
    ('/on-finish', 'tornado.routing:_RoutingDelegate'),
))
def test_concurrent_inbound_requests(app, uri, name):
    from tornado import gen
    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version

    @validate_transaction_count(2)
    @validate_transaction_metrics(
        name,
        rollup_metrics=((FRAMEWORK_METRIC, 1),),
    )
    def _test():
        url = app.get_url(uri)
        coros = (app.http_client.fetch(url) for _ in range(2))
        responses = app.io_loop.run_sync(lambda: gen.multi(coros))

        for response in responses:
            assert response.code == 200

    _test()


@override_generic_settings(global_settings(), {
    'enabled': False,
})
@function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
def test_nr_disabled(app):
    response = app.fetch('/simple')
    assert response.code == 200
