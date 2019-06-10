from benchmarks.util import MockApplication
from newrelic.api.background_task import BackgroundTaskWrapper
import six

DEF = """
import asyncio

@asyncio.coroutine
def _coro():
    while True:
        yield from asyncio.sleep(0.0)
"""


if six.PY3:
    class Suite(object):
        def setup(self):
            exec(DEF, globals())
            app = MockApplication()
            self.wrapped_coro = BackgroundTaskWrapper(_coro, application=app, name="test")()

        def teardown(self):
            self.wrapped_coro.close()

        def time_wrapped_coro_send(self):
            self.wrapped_coro.send(None)

        def peakmem_wrapped_coro_send(self):
            self.wrapped_coro.send(None)
