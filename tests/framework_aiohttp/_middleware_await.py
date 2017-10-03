async def load_coro_awaits(app, handler):

    async def coro_awaits(request):
        return await handler(request)

    return coro_awaits
