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

from elasticsearch import VERSION
from elasticsearch.serializer import JSONSerializer

try:
    from elasticsearch.transport import Transport
    from elasticsearch.connection.http_requests import RequestsHttpConnection
    from elasticsearch.connection.http_urllib3 import Urllib3HttpConnection
    NodeConfig = dict
    is_v8 = False
except ImportError:
    from elastic_transport._transport import Transport
    from elastic_transport._models import NodeConfig
    is_v8 = True


from testing_support.db_settings import elasticsearch_settings

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction


SKIP_IF_V7 = pytest.mark.skipif(not is_v8, reason="Skipping v8 tests.")
SKIP_IF_V8 = pytest.mark.skipif(is_v8, reason="Skipping v7 tests.")

ES_SETTINGS = elasticsearch_settings()[0]
HOST = NodeConfig(host=ES_SETTINGS["host"], port=int(ES_SETTINGS["port"]))

INDEX = "contacts"
DOC_TYPE = "person"
ID = 1
METHOD = "/contacts/person/1"
# METHOD = _make_path(INDEX, DOC_TYPE, ID)
PARAMS = {}
HEADERS = {"Content-Type": "application/json"}
DATA = {"name": "Joe Tester"}

BODY = JSONSerializer().dumps(DATA)
if hasattr(BODY, "encode"):
    BODY = BODY.encode("utf-8")


@SKIP_IF_V8
@background_task()
def test_transport_get_connection():
    transaction = current_transaction()
    
    transport = Transport([HOST])
    transport.get_connection()

    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected


@SKIP_IF_V7
@background_task()
def test_transport_perform_request():
    transaction = current_transaction()
    
    transport = Transport([HOST])
    transport.perform_request("POST", METHOD, headers=HEADERS, params=PARAMS, body=DATA)

    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected


@SKIP_IF_V8
@background_task()
def test_transport_perform_request_urllib3():
    transaction = current_transaction()
    
    transport = Transport([HOST], connection_class=Urllib3HttpConnection)
    if VERSION >= (7, 16, 0):
        transport.perform_request("POST", METHOD, headers=HEADERS, params=PARAMS, body=DATA)
    else:
        transport.perform_request("POST", METHOD, params=PARAMS, body=DATA)
    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected


@SKIP_IF_V8
@background_task()
def test_transport_perform_request_requests():
    transaction = current_transaction()
    
    transport = Transport([HOST], connection_class=RequestsHttpConnection)
    if VERSION >= (7, 16, 0):
        transport.perform_request("POST", METHOD, headers=HEADERS, params=PARAMS, body=DATA)
    else:
        transport.perform_request("POST", METHOD, params=PARAMS, body=DATA)

    expected = (ES_SETTINGS["host"], ES_SETTINGS["port"], None)
    assert transaction._nr_datastore_instance_info == expected
