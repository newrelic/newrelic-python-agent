import random
import pytest
import asyncio
import asyncpg

from io import BytesIO

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics
from utils import DB_SETTINGS


@validate_transaction_metrics(
    "test_single",
    background_task=True,
    scoped_metrics=(("Datastore/operation/Postgres/select", 1),),
    rollup_metrics=(("Datastore/operation/Postgres/select", 1), ("Datastore/all", 2)),
)
@background_task(name="test_single")
@pytest.mark.parametrize("method", ("execute",))
def test_single(method):
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        _method = getattr(conn, method)
        await _method("""SELECT 0""")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_prepared_single",
    background_task=True,
    scoped_metrics=(
        ("Datastore/operation/Postgres/prepare", 1),
        ("Datastore/operation/Postgres/select", 1),
    ),
    rollup_metrics=(
        ("Datastore/operation/Postgres/prepare", 1),
        ("Datastore/operation/Postgres/select", 1),
        ("Datastore/all", 3),
    ),
)
@background_task(name="test_prepared_single")
@pytest.mark.parametrize("method", ("fetch", "fetchrow", "fetchval"))
def test_prepared_single(method):
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        _method = getattr(conn, method)
        await _method("""SELECT 0""")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_prepare",
    background_task=True,
    scoped_metrics=(("Datastore/operation/Postgres/prepare", 1),),
    rollup_metrics=(("Datastore/operation/Postgres/prepare", 1), ("Datastore/all", 2)),
)
@background_task(name="test_prepare")
def test_prepare():
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        await conn.prepare("""SELECT 0""")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_copy",
    background_task=True,
    scoped_metrics=(
        ("Datastore/operation/Postgres/prepare", 1),
        ("Datastore/operation/Postgres/copy", 3),
    ),
    rollup_metrics=(("Datastore/operation/Postgres/copy", 3), ("Datastore/all", 8)),
)
@background_task(name="test_copy")
def test_copy():
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        temp_table = "table_%d" % random.randint(0, 2 ** 20)
        await conn.execute("""drop table if exists %s""" % temp_table)
        try:
            await conn.execute(
                """create table %s (a integer, b real, c text)""" % temp_table
            )

            await conn.copy_records_to_table(
                temp_table, records=[(1, 2, "3"), (4, 5, "6")]
            )
            await conn.copy_from_table(temp_table, output=BytesIO())

            # Causes a prepare and copy statement to be executed
            # 2 statements
            await conn.copy_from_query("""SELECT 0""", output=BytesIO())
        finally:
            await conn.execute("""drop table if exists %s""" % temp_table)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_select_many",
    background_task=True,
    scoped_metrics=(
        ("Datastore/operation/Postgres/prepare", 1),
        ("Datastore/operation/Postgres/select", 1),
    ),
    rollup_metrics=(
        ("Datastore/operation/Postgres/prepare", 1),
        ("Datastore/operation/Postgres/select", 1),
        ("Datastore/all", 3),
    ),
)
@background_task(name="test_select_many")
def test_select_many():
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        await conn.executemany("""SELECT $1::int""", ((1,), (2,)))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_transaction",
    background_task=True,
    scoped_metrics=(
        ("Datastore/operation/Postgres/begin", 1),
        ("Datastore/operation/Postgres/commit", 1),
        ("Datastore/operation/Postgres/select", 1),
    ),
    rollup_metrics=(
        ("Datastore/operation/Postgres/begin", 1),
        ("Datastore/operation/Postgres/commit", 1),
        ("Datastore/operation/Postgres/select", 1),
        ("Datastore/all", 4),
    ),
)
@background_task(name="test_transaction")
def test_transaction():
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        async with conn.transaction():
            await conn.execute("""SELECT 0""")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_cursor",
    background_task=True,
    scoped_metrics=(
        ("Datastore/operation/Postgres/begin", 1),
        ("Datastore/operation/Postgres/commit", 1),
        ("Datastore/operation/Postgres/prepare", 2),
        ("Datastore/operation/Postgres/select", 3),
    ),
    rollup_metrics=(
        ("Datastore/operation/Postgres/begin", 1),
        ("Datastore/operation/Postgres/commit", 1),
        ("Datastore/operation/Postgres/prepare", 2),
        ("Datastore/operation/Postgres/select", 3),
        ("Datastore/all", 8),
    ),
)
@background_task(name="test_cursor")
def test_cursor():
    async def amain():
        conn = await asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
        )

        async with conn.transaction():
            async for record in conn.cursor("SELECT generate_series(0, 0)", prefetch=1):
                pass

            await conn.cursor("SELECT 0")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())
