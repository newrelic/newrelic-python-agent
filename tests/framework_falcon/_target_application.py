import inspect
import falcon
import webtest


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


application = falcon.API()


def bad_error_handler(*args, **kwargs):
    bound = inspect.getcallargs(application._handle_exception, *args, **kwargs)
    resp = bound['resp']

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
