# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, ES_VERSION 2.0 (the "License");
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
from conftest import ES_SETTINGS, ES_URL, ES_VERSION, RUN_IF_V8_OR_ABOVE
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

try:
    # v8+
    from elastic_transport._node._http_aiohttp import AiohttpHttpNode as AIOHttpConnection
    from elastic_transport._node._http_httpx import HttpxAsyncHttpNode
except ImportError:
    # v7
    from elasticsearch._async.http_aiohttp import AIOHttpConnection

    HttpxAsyncHttpNode = None  # Not implemented in v7

HOST = instance_hostname(ES_SETTINGS["host"])
PORT = ES_SETTINGS["port"]


async def _exercise_es(es):
    if ES_VERSION >= (8,):
        await es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    else:
        await es.index(
            index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1
        )


@pytest.mark.parametrize(
    "client_kwargs",
    [
        pytest.param({"node_class": HttpxAsyncHttpNode}, id="HttpxAsyncHttpNodeV8", marks=RUN_IF_V8_OR_ABOVE),
        pytest.param({"node_class": AIOHttpConnection}, id="AIOHttpConnection"),
    ],
)
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_async_transport:test_async_transport_connection_classes",
    rollup_metrics=[(f"Datastore/instance/Elasticsearch/{HOST}/{PORT}", 1)],
    scoped_metrics=[(f"Datastore/instance/Elasticsearch/{HOST}/{PORT}", None)],
    background_task=True,
)
@background_task()
def test_async_transport_connection_classes(loop, client_kwargs):
    from elasticsearch import AsyncElasticsearch

    async_client = AsyncElasticsearch(ES_URL, **client_kwargs)
    loop.run_until_complete(_exercise_es(async_client))
    loop.run_until_complete(async_client.close())
