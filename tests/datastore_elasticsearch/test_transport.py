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

from elasticsearch.serializer import JSONSerializer

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

from conftest import ES_VERSION, ES_SETTINGS

try:
    from elasticsearch.transport import Transport
    from elasticsearch.connection.http_requests import RequestsHttpConnection
    from elasticsearch.connection.http_urllib3 import Urllib3HttpConnection

    NodeConfig = dict
except ImportError:
    from elastic_transport._models import NodeConfig
    from elastic_transport._transport import Transport

    from elastic_transport._node._http_requests import RequestsHttpNode as RequestsHttpConnection
    from elastic_transport._node._http_urllib3 import Urllib3HttpNode as Urllib3HttpConnection


IS_V8 = ES_VERSION >= (8,)
SKIP_IF_V7 = pytest.mark.skipif(not IS_V8, reason="Skipping v8 tests.")
SKIP_IF_V8 = pytest.mark.skipif(IS_V8, reason="Skipping v7 tests.")

HOST = NodeConfig(scheme="http", host=ES_SETTINGS["host"], port=int(ES_SETTINGS["port"]))

METHOD = "/contacts/person/1"
HEADERS = {"Content-Type": "application/json"}
DATA = {"name": "Joe Tester"}

BODY = JSONSerializer().dumps(DATA)
if hasattr(BODY, "encode"):
    BODY = BODY.encode("utf-8")


@pytest.mark.parametrize("transport_kwargs", [
    pytest.param({}, id="DefaultTransport"),
    pytest.param({"connection_class": Urllib3HttpConnection}, id="Urllib3HttpConnectionv7", marks=SKIP_IF_V8),
    pytest.param({"connection_class": RequestsHttpConnection}, id="RequestsHttpConnectionv7", marks=SKIP_IF_V8),
    pytest.param({"node_class": Urllib3HttpConnection}, id="Urllib3HttpNodev8", marks=SKIP_IF_V7),
    pytest.param({"node_class": RequestsHttpConnection}, id="RequestsHttpNodev8", marks=SKIP_IF_V7),
])
@background_task()
def test_transport_connection_classes(transport_kwargs):
    transaction = current_transaction()

    transport = Transport([HOST], **transport_kwargs)
    transport.perform_request("POST", METHOD, headers=HEADERS, body=DATA)

    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected
