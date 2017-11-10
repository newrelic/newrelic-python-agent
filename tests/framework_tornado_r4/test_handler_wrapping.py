import pytest
import tornado.web


def get_handlers():
    class BaseHandler(tornado.web.RequestHandler):
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
def test_handlers_wrapped(handler_name1, handler_name2):

    # get new instances of the handler classes
    handler_fixtures = get_handlers()
    handler1 = handler_fixtures.get(handler_name1, None)
    handler2 = handler_fixtures.get(handler_name2, None)

    # sanity check
    assert not hasattr(handler1, '_nr_wrap_complete')
    assert not hasattr(handler2, '_nr_wrap_complete')

    handlers = [(r'/handler1', handler1)]
    if handler2:
        handlers.append((r'/handler2', handler2))

    # apply the instrumentation
    tornado.web.Application(handlers)

    for _, handler in handlers:
        assert handler._nr_wrap_complete
        assert hasattr(handler.on_finish, '__wrapped__')
        assert not hasattr(handler.on_finish.__wrapped__, '__wrapped__')

        for request_method in handler.SUPPORTED_METHODS:
            method = getattr(handler, request_method.lower(), None)
            if method:
                assert hasattr(method, '__wrapped__')
                assert not hasattr(method.__wrapped__, '__wrapped__')


def test_multiple_applications():

    # get new instances of the handler classes
    handler_fixtures = get_handlers()
    handler1 = handler_fixtures.get('BaseHandler')

    # sanity check
    assert not hasattr(handler1, '_nr_wrap_complete')

    handlers = [(r'/handler1', handler1)]

    # apply the instrumentation
    tornado.web.Application(handlers)

    # apply the instrumentation again
    tornado.web.Application(handlers)

    # confirm we haven't double wrapped anything
    for _, handler in handlers:
        assert handler._nr_wrap_complete
        assert hasattr(handler.on_finish, '__wrapped__')
        assert not hasattr(handler.on_finish.__wrapped__, '__wrapped__')

        for request_method in handler.SUPPORTED_METHODS:
            method = getattr(handler, request_method.lower(), None)
            if method:
                assert hasattr(method, '__wrapped__')
                assert not hasattr(method.__wrapped__, '__wrapped__')
