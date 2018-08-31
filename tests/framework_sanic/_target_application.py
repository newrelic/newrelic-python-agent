from sanic import Sanic
from sanic.response import json
from sanic.exceptions import NotFound

app = Sanic()


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


@app.route('/404')
async def not_found(request):
    raise NotFound("Hey, where'd it go?")


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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
