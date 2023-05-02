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
from conftest import ES_SETTINGS, ES_VERSION
from elasticsearch.serializer import JSONSerializer

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

try:
    from elasticsearch.connection.http_requests import RequestsHttpConnection
    from elasticsearch.connection.http_urllib3 import Urllib3HttpConnection
    from elasticsearch.transport import Transport

    NodeConfig = dict
except ImportError:
    from elastic_transport._models import NodeConfig
    from elastic_transport._node._http_requests import (
        RequestsHttpNode as RequestsHttpConnection,
    )
    from elastic_transport._node._http_urllib3 import (
        Urllib3HttpNode as Urllib3HttpConnection,
    )
    from elastic_transport._transport import Transport


IS_V8 = ES_VERSION >= (8,)
IS_V7 = ES_VERSION >= (7,) and ES_VERSION < (8, 0)
IS_BELOW_V7 = ES_VERSION < (7,)

RUN_IF_V8 = pytest.mark.skipif(IS_V7 or IS_BELOW_V7, reason="Only run for v8+")
RUN_IF_V7 = pytest.mark.skipif(IS_V8 or IS_BELOW_V7, reason="Only run for v7")
RUN_IF_BELOW_V7 = pytest.mark.skipif(not IS_BELOW_V7, reason="Only run for versions below v7")


HOST = NodeConfig(scheme="http", host=ES_SETTINGS["host"], port=int(ES_SETTINGS["port"]))

METHOD = "/contacts/person/1"
HEADERS = {"Content-Type": "application/json"}
DATA = {"name": "Joe Tester"}

BODY = JSONSerializer().dumps(DATA)
if hasattr(BODY, "encode"):
    BODY = BODY.encode("utf-8")


@pytest.mark.parametrize(
    "transport_kwargs, perform_request_kwargs",
    [
        pytest.param({}, {"body": DATA}, id="DefaultTransport_below_v7", marks=RUN_IF_BELOW_V7),
        pytest.param({}, {"headers": HEADERS, "body": DATA}, id="DefaultTransport_v7+", marks=RUN_IF_V7 or RUN_IF_V8),
        pytest.param(
            {"connection_class": Urllib3HttpConnection},
            {"body": DATA},
            id="Urllib3HttpConnectionv7",
            marks=RUN_IF_BELOW_V7,
        ),
        pytest.param(
            {"connection_class": RequestsHttpConnection},
            {"body": DATA},
            id="RequestsHttpConnectionv7",
            marks=RUN_IF_BELOW_V7,
        ),
        pytest.param(
            {"connection_class": Urllib3HttpConnection},
            {"headers": HEADERS, "body": DATA},
            id="Urllib3HttpConnectionv7",
            marks=RUN_IF_V7,
        ),
        pytest.param(
            {"connection_class": RequestsHttpConnection},
            {"headers": HEADERS, "body": DATA},
            id="RequestsHttpConnectionv7",
            marks=RUN_IF_V7,
        ),
        pytest.param(
            {"node_class": Urllib3HttpConnection},
            {"headers": HEADERS, "body": DATA},
            id="Urllib3HttpNodev8",
            marks=RUN_IF_V8,
        ),
        pytest.param(
            {"node_class": RequestsHttpConnection},
            {"headers": HEADERS, "body": DATA},
            id="RequestsHttpNodev8",
            marks=RUN_IF_V8,
        ),
    ],
)
@background_task()
def test_transport_connection_classes(transport_kwargs, perform_request_kwargs):
    transaction = current_transaction()

    transport = Transport([HOST], **transport_kwargs)
    transport.perform_request("POST", METHOD, **perform_request_kwargs)

    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected
