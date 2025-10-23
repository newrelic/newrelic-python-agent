import asyncio

from newrelic.hooks.database_aiomysql import AsyncConnectionWrapper, wrap_pool__acquire


class DummyPool:
    _conn_kwargs = {"host": "localhost"}


class DummyDBModule:
    _nr_database_product = "MySQL"


def test_pool_acquire_does_not_double_wrap():
    async def run():
        connection_store = {"value": object()}

        async def underlying_acquire(*_args, **_kwargs):
            return connection_store["value"]

        wrapper = wrap_pool__acquire(DummyDBModule)
        pool = DummyPool()

        first = await wrapper(underlying_acquire, pool, (), {})
        assert isinstance(first, AsyncConnectionWrapper)
        inner = first._nr_next_object
        assert not isinstance(inner, AsyncConnectionWrapper)

        # Simulate connection being returned to the pool. The pool will now hand
        # back the already wrapped connection when acquire() is invoked again.
        connection_store["value"] = first

        second = await wrapper(underlying_acquire, pool, (), {})
        assert second is first
        assert not isinstance(second._nr_next_object, AsyncConnectionWrapper)
    asyncio.run(run())
