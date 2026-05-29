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

import asyncio
from threading import Event

from langgraph.pregel._executor import AsyncBackgroundExecutor, BackgroundExecutor

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace


@background_task()
def test_background_executor_submit_propagates_context():
    trace = current_trace()
    test_ran = Event()

    def task():
        assert current_trace() is trace
        test_ran.set()

    with BackgroundExecutor(config={}) as submit:
        future = submit(task)
        future.result()

    assert test_ran.is_set()


@background_task()
def test_async_background_executor_submit_propagates_context(loop):
    trace = current_trace()
    test_ran = Event()

    async def task():
        assert current_trace() is trace
        test_ran.set()

    async def _test():
        async with AsyncBackgroundExecutor(config={}) as submit:
            future = submit(task)
            await asyncio.wrap_future(future)

    loop.run_until_complete(_test())

    assert test_ran.is_set()


def test_background_executor_submit_pass_through_outside_transaction():
    test_ran = Event()

    def task():
        test_ran.set()

    with BackgroundExecutor(config={}) as submit:
        submit(task).result()

    assert test_ran.is_set()


def test_async_background_executor_submit_pass_through_outside_transaction(loop):
    test_ran = Event()

    async def task():
        test_ran.set()

    async def _test():
        async with AsyncBackgroundExecutor(config={}) as submit:
            await asyncio.wrap_future(submit(task))

    loop.run_until_complete(_test())

    assert test_ran.is_set()
