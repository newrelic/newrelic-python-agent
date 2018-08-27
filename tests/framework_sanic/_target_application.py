from sanic import Sanic
from sanic.response import json

app = Sanic()


@app.route('/')
async def index(request):
    return json({'hello': 'world'})


@app.route('/misnamed')
async def misnamed(request):
    return json({'hello': 'world'})


del misnamed._nr_handler_name


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
