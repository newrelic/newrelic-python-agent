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
import pytest


@pytest.mark.parametrize(
    "method",
    (
        "get",
        "options",
        "head",
        "post",
        "put",
        "patch",
        "delete",
        "send",
    ),
)
@pytest.mark.xfail(
    reason="Not implemented yet", strict=True, raises=NotImplementedError
)
def test_sync_client(httpx, server, method):
    with httpx.Client() as client:
        method = getattr(client, method)
        response = method("http://localhost:%s" % server.port)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "method",
    (
        "get",
        "options",
        "head",
        "post",
        "put",
        "patch",
        "delete",
        "send",
    ),
)
@pytest.mark.xfail(
    reason="Not implemented yet", strict=True, raises=NotImplementedError
)
def test_async_client(httpx, server, loop, method):
    async def test_async_client():
        async with httpx.AsyncClient() as client:
            resolved_method = getattr(client, method)
            responses = await asyncio.gather(
                resolved_method("http://localhost:%s" % server.port),
                resolved_method("http://localhost:%s" % server.port),
            )

        return responses

    responses = loop.run_until_complete(test_async_client())
    assert all(response.status == 200 for response in responses)
