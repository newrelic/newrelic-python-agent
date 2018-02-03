import pytest

from newrelic.common.object_wrapper import _NRBoundFunctionWrapper


def get_handlers(web):
    class BaseHandler(web.RequestHandler):
        def get(self):
            pass

    class MethodNotFoundHandler(BaseHandler):
        SUPPORTED_METHODS = BaseHandler.SUPPORTED_METHODS + ('TEAPOT', )

    class MethodNotSupportedHandler(BaseHandler):
        SUPPORTED_METHODS = ('POST', )

    class SubclassOverridesGetHandler(BaseHandler):
        def get(self):
            pass

    class SubclassOverridesPostHandler(BaseHandler):
        def post(self):
            pass

    class SubclassOverridesOnFinishHandler(BaseHandler):
        def on_finish(self):
            pass

    return {
        'BaseHandler': BaseHandler,
        'MethodNotFoundHandler': MethodNotFoundHandler,
        'MethodNotSupportedHandler': MethodNotSupportedHandler,
        'SubclassOverridesGetHandler': SubclassOverridesGetHandler,
        'SubclassOverridesPostHandler': SubclassOverridesPostHandler,
        'SubclassOverridesOnFinishHandler': SubclassOverridesOnFinishHandler,
    }


def get_handler(web):
    class BaseHandler(web.RequestHandler):
        def get(self):
            pass

    return BaseHandler


@pytest.fixture(scope='function')
def web():
    # prevent importing of tornado modules until test execution
    import tornado.web as web
    yield web


@pytest.mark.parametrize('handler_name1,handler_name2', [
        ('BaseHandler', None),
        ('MethodNotFoundHandler', None),
        ('MethodNotSupportedHandler', None),
        ('SubclassOverridesGetHandler', 'BaseHandler'),
        ('BaseHandler', 'SubclassOverridesGetHandler'),
        ('SubclassOverridesPostHandler', 'BaseHandler'),
        ('BaseHandler', 'SubclassOverridesPostHandler'),
        ('SubclassOverridesOnFinishHandler', 'BaseHandler'),
        ('BaseHandler', 'SubclassOverridesOnFinishHandler'),
])
def test_handlers_wrapped(handler_name1, handler_name2, web):

    # get new instances of the handler classes
    handler_fixtures = get_handlers(web)
    handler1 = handler_fixtures.get(handler_name1, None)
    handler2 = handler_fixtures.get(handler_name2, None)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)
    if handler2:
        assert not isinstance(handler2.on_finish, _NRBoundFunctionWrapper)

    handlers = [(r'/handler1', handler1)]
    if handler2:
        handlers.append((r'/handler2', handler2))

    # apply the instrumentation
    web.Application(handlers)

    for _, handler in handlers:
        assert hasattr(handler.on_finish, '__wrapped__')
        assert not hasattr(handler.on_finish.__wrapped__, '__wrapped__')

        for request_method in handler.SUPPORTED_METHODS:
            method = getattr(handler, request_method.lower(), None)
            if method:
                assert hasattr(method, '__wrapped__')
                assert not hasattr(method.__wrapped__, '__wrapped__')


def test_multiple_applications(web):

    # get new instance of the handler class
    handler1 = get_handler(web)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)

    handlers = [(r'/handler1', handler1)]

    # apply the instrumentation
    web.Application(handlers)

    # apply the instrumentation again
    web.Application(handlers)

    assert hasattr(handler1.on_finish, '__wrapped__')
    assert not hasattr(handler1.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        if method:
            assert hasattr(method, '__wrapped__')
            assert not hasattr(method.__wrapped__, '__wrapped__')


def test_non_class_based_view(web):

    def handler1():
        pass

    handlers = [(r'/handler1', handler1)]

    # apply the instrumentation
    web.Application(handlers)

    assert not isinstance(handler1, _NRBoundFunctionWrapper)
    assert not hasattr(handler1, 'on_finish')


def test_with_target_kwargs(web):

    # get new instance of the handler class
    handler1 = get_handler(web)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)

    handlers = [(r'/handler1', handler1, {'hello': 'world'})]

    # apply the instrumentation
    web.Application(handlers)

    assert hasattr(handler1.on_finish, '__wrapped__')
    assert not hasattr(handler1.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        if method:
            assert hasattr(method, '__wrapped__')
            assert not hasattr(method.__wrapped__, '__wrapped__')


def test_nested_routing(web):

    try:
        import tornado.routing
    except ImportError:
        # this is an earlier version of tornado, skip this test
        pytest.skip('No routing module in this Tornado version')

    # get new instance of the handler class
    handler1 = get_handler(web)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)

    web.Application([
        (tornado.routing.HostMatches('example.com'), [
            (r'/', handler1),
        ]),
    ])

    assert hasattr(handler1.on_finish, '__wrapped__')
    assert not hasattr(handler1.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        if method:
            assert hasattr(method, '__wrapped__')
            assert not hasattr(method.__wrapped__, '__wrapped__')


def test_add_handlers(web):

    # get new instance of the handler class
    handler1 = get_handler(web)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)

    handlers = [(r'/handler1', handler1)]
    app = web.Application()
    app.add_handlers(r'www.newrelic.com', handlers)

    assert hasattr(handler1.on_finish, '__wrapped__')
    assert not hasattr(handler1.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        if method:
            assert hasattr(method, '__wrapped__')
            assert not hasattr(method.__wrapped__, '__wrapped__')


def test_wrapping_subclass_does_not_wrap_parent_class(web):

    # get new instances of the handler classes
    handler_fixtures = get_handlers(web)
    handler1 = handler_fixtures.get('BaseHandler')
    handler2 = handler_fixtures.get('SubclassOverridesPostHandler')

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)
    assert not isinstance(handler2.on_finish, _NRBoundFunctionWrapper)

    # just use one handler
    handlers = [(r'/handler2', handler2)]

    # apply the instrumentation
    web.Application(handlers)

    # handler2 is wrapped
    assert hasattr(handler2.on_finish, '__wrapped__')
    assert not hasattr(handler2.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler2.SUPPORTED_METHODS:
        method = getattr(handler2, request_method.lower(), None)
        assert hasattr(method, '__wrapped__')
        assert not hasattr(method.__wrapped__, '__wrapped__')

    # handler1 is not wrapped
    assert not hasattr(handler1.on_finish, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        assert not hasattr(method, '__wrapped__')

    # confirm wrapping is not the same
    assert handler1.on_finish is not handler2.on_finish
    assert handler1.get is not handler2.get
    assert handler1.post is not handler2.post


def test_urlspecs(web):

    # get new instance of the handler class
    handler1 = get_handler(web)

    # sanity check
    assert not isinstance(handler1.on_finish, _NRBoundFunctionWrapper)

    handlers = [web.URLSpec(r'/handler1', handler1, name='handler1')]
    web.Application(handlers)

    assert hasattr(handler1.on_finish, '__wrapped__')
    assert not hasattr(handler1.on_finish.__wrapped__, '__wrapped__')

    for request_method in handler1.SUPPORTED_METHODS:
        method = getattr(handler1, request_method.lower(), None)
        if method:
            assert hasattr(method, '__wrapped__')
            assert not hasattr(method.__wrapped__, '__wrapped__')
