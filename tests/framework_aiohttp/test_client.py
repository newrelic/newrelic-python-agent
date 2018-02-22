import aiohttp
import sys

aiohttp_version = tuple(map(int, aiohttp.__version__.split('.')[:3]))

if sys.version_info >= (3, 5):
    from _test_client_async_await import *  # NOQA

if aiohttp_version < (3, 0):
    from _test_client_yield_from import *  # NOQA
