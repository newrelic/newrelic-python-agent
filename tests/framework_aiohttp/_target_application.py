# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import sys

from aiohttp import ClientSession, WSMsgType, web

from newrelic.api.function_trace import function_trace


async def index(request):
    await asyncio.sleep(0)
    resp = web.Response(text="Hello Aiohttp!")
    resp.set_cookie("ExampleCookie", "ExampleValue")
    return resp


async def hang(request):
    while True:
        await asyncio.sleep(0)


async def error(request):
    raise ValueError("Value Error")


async def non_500_error(request):
    raise web.HTTPGone()


async def raise_403(request):
    raise web.HTTPForbidden()


async def raise_404(request):
    raise web.HTTPNotFound()


@function_trace()
async def wait():
    await asyncio.sleep(0.1)


async def run_task(loop):
    await wait()
    loop.stop()


async def background(request):
    try:
        loop = request.loop
    except AttributeError:
        loop = request.task._loop

    asyncio.set_event_loop(loop)
    asyncio.tasks.ensure_future(run_task(loop))
    return web.Response(text="Background Task Scheduled")


class HelloWorldView(web.View):
    async def _respond(self):
        await asyncio.sleep(0)
        resp = web.Response(text="Hello Aiohttp!")
        resp.set_cookie("ExampleCookie", "ExampleValue")
        return resp

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


class KnownException(Exception):
    pass


class KnownErrorView(web.View):
    async def _respond(self):
        try:
            await asyncio.sleep(0)
        except KnownException:
            pass
        finally:
            return web.Response(text="Hello Aiohttp!")

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # receive messages for all eternity!
    # (or until the client closes the socket)
    while not ws.closed:
        msg = await ws.receive()
        if msg.type == WSMsgType.TEXT:
            result = ws.send_str("/" + msg.data)
            if hasattr(result, "__await__"):
                await result

    return ws


async def fetch(method, url, loop):
    session = ClientSession(loop=loop)

    if hasattr(session, "__aenter__"):
        await session.__aenter__()
    else:
        session.__enter__()

    try:
        _method = getattr(session, method)
        try:
            response = await asyncio.wait_for(_method(url), timeout=None, loop=loop)
        except TypeError:
            response = await asyncio.wait_for(_method(url), timeout=None)
        text = await response.text()

    finally:
        if hasattr(session, "__aexit__"):
            await session.__aexit__(*sys.exc_info())
        else:
            session.__exit__(*sys.exc_info())

    return text


async def fetch_multiple(method, loop, url):
    coros = [fetch(method, url, loop) for _ in range(2)]
    try:
        responses = await asyncio.gather(*coros, loop=loop)
    except TypeError:
        responses = await asyncio.gather(*coros)
    return "\n".join(responses)


async def multi_fetch_handler(request):
    try:
        loop = request.loop
    except AttributeError:
        loop = request.task._loop

    responses = await fetch_multiple("get", loop, request.query["url"])
    return web.Response(text=responses, content_type="text/html")


def make_app(middlewares=None):
    app = web.Application(middlewares=middlewares)
    app.router.add_route("*", "/coro", index)
    app.router.add_route("*", "/class", HelloWorldView)
    app.router.add_route("*", "/error", error)
    app.router.add_route("*", "/known_error", KnownErrorView)
    app.router.add_route("*", "/non_500_error", non_500_error)
    app.router.add_route("*", "/raise_403", raise_403)
    app.router.add_route("*", "/raise_404", raise_404)
    app.router.add_route("*", "/hang", hang)
    app.router.add_route("*", "/background", background)
    app.router.add_route("*", "/ws", websocket_handler)
    app.router.add_route("*", "/multi_fetch", multi_fetch_handler)

    for route in app.router.routes():
        handler = route.handler

        # https://github.com/aio-libs/aiohttp-cors/blob/73510a3a9212afd1d3740fd8b2feba63a1dcfe13/aiohttp_cors/urldispatcher_router_adapter.py#L95
        # Check that this statement passes for all routes
        # This statement was causing a crash since issubclass would error on
        # function wrappers
        isinstance(handler, type) and issubclass(handler, web.View)

    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="127.0.0.1")
