from sanic import Sanic
from sanic.exceptions import NotFound, SanicException
from sanic.handlers import ErrorHandler
from sanic.response import json, stream


class CustomErrorHandler(ErrorHandler):
    def response(self, request, exception):
        if isinstance(exception, ZeroDivisionError):
            raise ValueError('DOUBLE OOPS')
        else:
            return super(CustomErrorHandler, self).response(request, exception)


app = Sanic(error_handler=CustomErrorHandler())


@app.route('/')
async def index(request):
    return json({'hello': 'world'})


@app.route('/misnamed')
async def misnamed(request):
    return json({'hello': 'world'})


del misnamed._nr_handler_name


@app.route('/error')
async def error(request):
    raise ValueError('OOPS')


# see write_callback in confest.create_request_coroutine
@app.route('/write_response_error')
async def write_response_error(request):
    return json({'hello': 'wh-wh-whatever'})


@app.route('/404')
async def not_found(request):
    raise NotFound("Hey, where'd it go?")


@app.route('/zero')
async def zero_division_error(request):
    1 / 0


@app.middleware('request')
async def request_middleware(request):
    return None


# register the middleware a second time, testing that the `request_middleware`
# function is not getting double wrapped
app.register_middleware(request_middleware)


@app.middleware('response')
async def misnamed_response_middleware(request, response):
    return None


del misnamed_response_middleware._nr_middleware_name


@app.route('/streaming')
async def streaming(request):
    async def streaming_fn(response):
        response.write('foo')
        response.write('bar')
    return stream(streaming_fn)


@app.route('/custom-header/<header_key>/<header_value>')
async def custom_header(request, header_key, header_value):
    custom_headers = {header_key: header_value}
    return json({'hello': 'world'}, headers=custom_headers)


class CustomExceptionSync(SanicException):
    pass


class CustomExceptionAsync(SanicException):
    pass


@app.exception(CustomExceptionSync)
def handle_custom_exception_sync(request, exception):
    raise SanicException('something went very very wrong')


@app.exception(CustomExceptionAsync)
async def handle_custom_exception_async(request, exception):
    raise SanicException('something went very very wrong')


@app.route('/sync-error')
async def sync_error(request):
    raise CustomExceptionSync('something went wrong')


@app.route('/async-error')
async def async_error(request):
    raise CustomExceptionAsync('something went wrong')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
