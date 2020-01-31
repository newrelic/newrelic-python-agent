import falcon
import webtest


try:
    from falcon import HTTPRouteNotFound
    NOT_FOUND_ERROR_NAME = 'falcon.errors:HTTPRouteNotFound'
except ImportError:
    NOT_FOUND_ERROR_NAME = 'falcon.errors:HTTPNotFound'


def _bind_response(*args, **kwargs):
    args = list(args)
    args.extend(kwargs.values())
    for arg in args:
        if hasattr(arg, 'status'):
            return arg


class Oops(ValueError):
    pass


class Crash(ValueError):
    pass


class Index(object):
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.content_type = 'application/json'
        resp.data = b'{"status": "ok"}'


class BadResponse(object):
    def on_get(self, req, resp):
        raise Oops()

    def on_put(self, req, resp):
        raise Crash()


try:
    application = falcon.App()
    name_prefix = 'falcon.app:App'
except AttributeError:
    application = falcon.API()
    name_prefix = 'falcon.api:API'


def bad_error_handler(*args, **kwargs):
    resp = _bind_response(*args, **kwargs)

    # This endpoint is explicitly not doing the correct thing. Status is
    # expected to be a type str with a status code + explanation. The intent
    # here is to test what happens if we don't parse the response code
    # correctly.
    resp.status = 200


application.add_route('/', Index())
application.add_route('/bad_response', BadResponse())
application.add_error_handler(Oops, bad_error_handler)

_target_application = webtest.TestApp(application)

# Put exception class here for convenience
_target_application.Crash = Crash

# Put names here for convenience
_target_application.name_prefix = name_prefix
_target_application.not_found_error = NOT_FOUND_ERROR_NAME
