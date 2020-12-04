import asyncio


class Application:

    def __init__(self, scope):
        if scope['type'] != 'http':
            raise ValueError('Unsupported', scope['type'])
        self.scope = scope

    @asyncio.coroutine
    def __call__(self, receive, send):
        yield from send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'Content-Type', b'text/plain')],
        })

        yield from send({
            'type': 'http.response.body',
            'body': b'PONG',
        })
