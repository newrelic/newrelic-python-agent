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

from elasticsearch.client.utils import _make_path
from elasticsearch.transport import Transport
from elasticsearch.connection.http_requests import RequestsHttpConnection
from elasticsearch.connection.http_urllib3 import Urllib3HttpConnection
from elasticsearch.serializer import JSONSerializer

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import BackgroundTask

from testing_support.db_settings import elasticsearch_settings

ES_SETTINGS = elasticsearch_settings()[0]
HOST = {
    'host':ES_SETTINGS['host'],
    'port': int(ES_SETTINGS['port'])
}
INDEX = 'contacts'
DOC_TYPE = 'person'
ID = 1
METHOD = _make_path(INDEX, DOC_TYPE, ID)
PARAMS = {}
DATA = {"name": "Joe Tester"}
BODY = JSONSerializer().dumps(DATA).encode('utf-8')


def test_transport_get_connection():
    app = application()
    with BackgroundTask(app, 'transport_perform_request') as transaction:
        transport = Transport([HOST])
        transport.get_connection()

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected

def test_transport_perform_request_urllib3():
    app = application()
    with BackgroundTask(app, 'perform_request_urllib3') as transaction:
        transport = Transport([HOST], connection_class=Urllib3HttpConnection)
        transport.perform_request('POST', METHOD, params=PARAMS, body=DATA)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected

def test_transport_perform_request_requests():
    app = application()
    with BackgroundTask(app, 'perform_request_requests') as transaction:
        transport = Transport([HOST], connection_class=RequestsHttpConnection)
        transport.perform_request('POST', METHOD, params=PARAMS, body=DATA)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected
