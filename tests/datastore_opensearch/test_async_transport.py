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
from conftest import OPENSEARCH_SETTINGS, OPENSEARCH_URL
from opensearchpy.connection import AsyncHttpConnection
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

HOST = instance_hostname(OPENSEARCH_SETTINGS["host"])
PORT = OPENSEARCH_SETTINGS["port"]


async def _exercise_opensearch(client):
    await client.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)


@pytest.mark.parametrize(
    "client_kwargs",
    [
        pytest.param({}, id="DefaultConnection"),
        pytest.param({"connection_class": AsyncHttpConnection}, id="AsyncHttpConnection"),
    ],
)
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_async_transport:test_async_transport_connection_classes",
    rollup_metrics=[(f"Datastore/instance/OpenSearch/{HOST}/{PORT}", 1)],
    scoped_metrics=[(f"Datastore/instance/OpenSearch/{HOST}/{PORT}", None)],
    background_task=True,
)
@background_task()
def test_async_transport_connection_classes(loop, client_kwargs):
    from opensearchpy import AsyncOpenSearch

    async_client = AsyncOpenSearch(OPENSEARCH_URL, **client_kwargs)
    loop.run_until_complete(_exercise_opensearch(async_client))
    loop.run_until_complete(async_client.close())
