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

import os
import random
import pytest
import asyncio
import asyncpg

from io import BytesIO

from newrelic.api.background_task import background_task
from testing_support.fixtures import (
    validate_transaction_metrics,
    validate_tt_collector_json,
)
from testing_support.util import instance_hostname
from testing_support.db_settings import postgresql_settings

DB_SETTINGS = postgresql_settings()[0]


PG_PREFIX = "Datastore/operation/Postgres/"
ASYNCPG_VERSION = tuple(
    int(x) for x in getattr(asyncpg, "__version__", "0.0").split(".")[:2]
)

if ASYNCPG_VERSION < (0, 11):
    CONNECT_METRICS = ()
else:
    CONNECT_METRICS = ((PG_PREFIX + "connect", 1),)


@pytest.fixture
def conn():
    loop = asyncio.get_event_loop()
    conn = loop.run_until_complete(
        asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
        )
    )
    yield conn
    loop.run_until_complete(conn.close())


@validate_transaction_metrics(
    "test_single",
    background_task=True,
    scoped_metrics=((PG_PREFIX + "select", 1),),
    rollup_metrics=(("Datastore/all", 1),),
)
@validate_tt_collector_json(
    datastore_params={"port_path_or_id": str(DB_SETTINGS["port"])}
)
@background_task(name="test_single")
@pytest.mark.parametrize("method", ("execute",))
def test_single(method, conn):
    _method = getattr(conn, method)
    asyncio.get_event_loop().run_until_complete(_method("""SELECT 0"""))


@validate_transaction_metrics(
    "test_prepared_single",
    background_task=True,
    scoped_metrics=(
        (PG_PREFIX + "prepare", 1),
        (PG_PREFIX + "select", 1),
    ),
    rollup_metrics=(("Datastore/all", 2),),
)
@background_task(name="test_prepared_single")
@pytest.mark.parametrize("method", ("fetch", "fetchrow", "fetchval"))
def test_prepared_single(method, conn):
    _method = getattr(conn, method)
    asyncio.get_event_loop().run_until_complete(_method("""SELECT 0"""))


@validate_transaction_metrics(
    "test_prepare",
    background_task=True,
    scoped_metrics=((PG_PREFIX + "prepare", 1),),
    rollup_metrics=(("Datastore/all", 1),),
)
@background_task(name="test_prepare")
def test_prepare(conn):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(conn.prepare("""SELECT 0"""))


@pytest.fixture
def table(conn):
    table_name = "table_%d" % os.getpid()

    asyncio.get_event_loop().run_until_complete(
        conn.execute("""create table %s (a integer, b real, c text)""" % table_name)
    )

    return table_name


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11), reason="Copy wasn't implemented before 0.11"
)
@validate_transaction_metrics(
    "test_copy",
    background_task=True,
    scoped_metrics=(
        (PG_PREFIX + "prepare", 1),
        (PG_PREFIX + "copy", 3),
    ),
    rollup_metrics=(("Datastore/all", 4),),
)
@background_task(name="test_copy")
def test_copy(table, conn):
    async def amain():
        await conn.copy_records_to_table(table, records=[(1, 2, "3"), (4, 5, "6")])
        await conn.copy_from_table(table, output=BytesIO())

        # Causes a prepare and copy statement to be executed
        # 2 statements
        await conn.copy_from_query("""SELECT 0""", output=BytesIO())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_select_many",
    background_task=True,
    scoped_metrics=(
        (PG_PREFIX + "prepare", 1),
        (PG_PREFIX + "select", 1),
    ),
    rollup_metrics=(("Datastore/all", 2),),
)
@background_task(name="test_select_many")
def test_select_many(conn):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(conn.executemany("""SELECT $1::int""", ((1,), (2,))))


@validate_transaction_metrics(
    "test_transaction",
    background_task=True,
    scoped_metrics=(
        (PG_PREFIX + "begin", 1),
        (PG_PREFIX + "select", 1),
        (PG_PREFIX + "commit", 1),
    ),
    rollup_metrics=(("Datastore/all", 3),),
)
@background_task(name="test_transaction")
def test_transaction(conn):
    async def amain():
        async with conn.transaction():
            await conn.execute("""SELECT 0""")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_cursor",
    background_task=True,
    scoped_metrics=(
        (PG_PREFIX + "begin", 1),
        (PG_PREFIX + "prepare", 2),
        (PG_PREFIX + "select", 3),
        (PG_PREFIX + "commit", 1),
    ),
    rollup_metrics=(("Datastore/all", 7),),
)
@background_task(name="test_cursor")
def test_cursor(conn):
    async def amain():
        async with conn.transaction():
            async for record in conn.cursor("SELECT generate_series(0, 0)", prefetch=1):
                pass

            await conn.cursor("SELECT 0")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11),
    reason="This is testing connect behavior which is only captured on newer asyncpg versions",
)
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
    loop = asyncio.get_event_loop()
    with pytest.raises(OSError):
        loop.run_until_complete(
            asyncpg.connect("postgres://?host=/.s.PGSQL.THIS_FILE_BETTER_NOT_EXIST")
        )


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11),
    reason="This is testing connect behavior which is only captured on newer asyncpg versions",
)
@validate_transaction_metrics(
    "test_pool_acquire",
    background_task=True,
    scoped_metrics=((PG_PREFIX + "connect", 2),),
)
@background_task(name="test_pool_acquire")
def test_pool_acquire():
    async def amain():
        pool = await asyncpg.create_pool(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            min_size=1,
        )

        try:
            async with pool.acquire():
                async with pool.acquire():
                    pass

        finally:
            await pool.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain())
