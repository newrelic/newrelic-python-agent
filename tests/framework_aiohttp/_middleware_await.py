async def load_logic_blimps(app, handler):

    async def logic_blimps(request):
        try:
            return await handler(request)
        except Exception as e:
            return web.Response(status=418, text=str(e))

    return logic_blimps
