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
        transport.perform_request('POST', METHOD, PARAMS, DATA)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected

def test_transport_perform_request_requests():
    app = application()
    with BackgroundTask(app, 'perform_request_requests') as transaction:
        transport = Transport([HOST], connection_class=RequestsHttpConnection)
        transport.perform_request('POST', METHOD, PARAMS, DATA)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected
