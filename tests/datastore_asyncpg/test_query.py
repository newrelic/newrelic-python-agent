import random
import pytest
import asyncio
import asyncpg

from io import BytesIO

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics
from testing_support.util import instance_hostname
from utils import DB_SETTINGS


PG_PREFIX = "Datastore/operation/Postgres/"
ASYNCPG_VERSION = tuple(
    int(x) for x in getattr(asyncpg, "__version__", "0.0").split(".")[:2]
)

if ASYNCPG_VERSION < (0, 11):
    CONNECT_METRICS = ()
else:
    CONNECT_METRICS = ((PG_PREFIX + "connect", 1),)


@validate_transaction_metrics(
    "test_single",
    background_task=True,
    scoped_metrics=CONNECT_METRICS + ((PG_PREFIX + "select", 1),),
    rollup_metrics=(("Datastore/all", 1 + len(CONNECT_METRICS)),),
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
    scoped_metrics=CONNECT_METRICS
    + ((PG_PREFIX + "prepare", 1), (PG_PREFIX + "select", 1),),
    rollup_metrics=(("Datastore/all", 2 + len(CONNECT_METRICS)),),
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
    scoped_metrics=CONNECT_METRICS + ((PG_PREFIX + "prepare", 1),),
    rollup_metrics=(("Datastore/all", 1 + len(CONNECT_METRICS)),),
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


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11), reason="Copy wasn't implemented before 0.11"
)
@validate_transaction_metrics(
    "test_copy",
    background_task=True,
    scoped_metrics=CONNECT_METRICS
    + (
        (PG_PREFIX + "drop", 2),
        (PG_PREFIX + "create", 1),
        (PG_PREFIX + "prepare", 1),
        (PG_PREFIX + "copy", 3),
    ),
    rollup_metrics=(("Datastore/all", 7 + len(CONNECT_METRICS)),),
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
    scoped_metrics=CONNECT_METRICS
    + ((PG_PREFIX + "prepare", 1), (PG_PREFIX + "select", 1),),
    rollup_metrics=(("Datastore/all", 2 + len(CONNECT_METRICS)),),
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
    scoped_metrics=CONNECT_METRICS
    + ((PG_PREFIX + "begin", 1), (PG_PREFIX + "select", 1), (PG_PREFIX + "commit", 1),),
    rollup_metrics=(("Datastore/all", 3 + len(CONNECT_METRICS)),),
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
    scoped_metrics=CONNECT_METRICS
    + (
        (PG_PREFIX + "begin", 1),
        (PG_PREFIX + "prepare", 2),
        (PG_PREFIX + "select", 3),
        (PG_PREFIX + "commit", 1),
    ),
    rollup_metrics=(("Datastore/all", 7 + len(CONNECT_METRICS)),),
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


@validate_transaction_metrics(
    "test_unix_socket_connect",
    background_task=True,
    rollup_metrics=[
        (
            "Datastore/instance/Postgres/"
            + instance_hostname("localhost")
            + "//.s.PGSQL.THIS_FILE_BETTER_NOT_EXIST",
            1,
        )
    ],
)
@background_task(name="test_unix_socket_connect")
def test_unix_socket_connect():
    async def amain():
        with pytest.raises(OSError):
            await asyncpg.connect(
                "postgres://?host=/.s.PGSQL.THIS_FILE_BETTER_NOT_EXIST"
            )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())
