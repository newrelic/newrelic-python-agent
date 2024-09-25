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

import pytest
from conftest import AIOREDIS_VERSION, SKIPIF_AIOREDIS_V1, SKIPIF_AIOREDIS_V2
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)

from newrelic.api.background_task import background_task


@background_task()
@pytest.mark.parametrize("in_transaction", (True, False))
def test_pipelines_no_harm(client, in_transaction, loop, key):
    async def exercise():
        if AIOREDIS_VERSION >= (2,):
            pipe = client.pipeline(transaction=in_transaction)
        else:
            pipe = client.pipeline()  # Transaction kwarg unsupported

        pipe.set(key, 1)
        return await pipe.execute()

    status = loop.run_until_complete(exercise())
    assert status == [True]


def exercise_transaction_sync(key):
    def _run(pipe):
        pipe.set(key, 1)
    return _run


def exercise_transaction_async(key):
    async def _run(pipe):
        await pipe.set(key, 1)
    return _run


@SKIPIF_AIOREDIS_V1
@pytest.mark.parametrize("exercise", (exercise_transaction_sync, exercise_transaction_async))
@background_task()
def test_transactions_no_harm(client, loop, key, exercise):
    status = loop.run_until_complete(client.transaction(exercise(key)))
    assert status == [True]


@SKIPIF_AIOREDIS_V2
@background_task()
def test_multi_exec_no_harm(client, loop, key):
    async def exercise():
        pipe = client.multi_exec()
        pipe.set(key, "value")
        status = await pipe.execute()
        assert status == [True]

    loop.run_until_complete(exercise())


@SKIPIF_AIOREDIS_V1
@background_task()
def test_pipeline_immediate_execution_no_harm(client, loop, key):
    async def exercise():
        await client.set(key, 1)

        if AIOREDIS_VERSION >= (2,):
            pipe = client.pipeline(transaction=True)
        else:
            pipe = client.pipeline()  # Transaction kwarg unsupported

        async with pipe:
            await pipe.watch(key)
            value = int(await pipe.get(key))
            assert value == 1
            value += 1
            pipe.multi()
            pipe.set(key, value)
            await pipe.execute()

        assert int(await client.get(key)) == 2

    loop.run_until_complete(exercise())


@SKIPIF_AIOREDIS_V1
@background_task()
def test_transaction_immediate_execution_no_harm(client, loop, key):
    async def exercise():
        async def exercise_transaction(pipe):
            value = int(await pipe.get(key))
            assert value == 1
            value += 1
            pipe.multi()
            pipe.set(key, value)
            await pipe.execute()

        await client.set(key, 1)
        status = await client.transaction(exercise_transaction, key)
        assert int(await client.get(key)) == 2

        return status

    status = loop.run_until_complete(exercise())
    assert status == []


@SKIPIF_AIOREDIS_V1
@validate_transaction_errors([])
@background_task()
def test_transaction_watch_error_no_harm(client, loop, key):
    async def exercise():
        async def exercise_transaction(pipe):
            value = int(await pipe.get(key))
            if value == 1:
                # Only run set the first pass, as this runs repeatedly until no watch error is raised.
                await pipe.set(key, 2)

        await client.set(key, 1)
        status = await client.transaction(exercise_transaction, key)

        return status

    status = loop.run_until_complete(exercise())
    assert status == []
