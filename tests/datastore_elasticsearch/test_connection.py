from newrelic.agent import application, BackgroundTask

from elasticsearch.client.utils import _make_path
from elasticsearch.connection.base import Connection
from elasticsearch.connection.http_requests import RequestsHttpConnection
from elasticsearch.connection.http_urllib3 import Urllib3HttpConnection
from elasticsearch.serializer import JSONSerializer

from testing_support.settings import elasticsearch_multiple_settings

ES_SETTINGS = elasticsearch_multiple_settings()[0]

INDEX = 'contacts'
DOC_TYPE = 'person'
ID = 1
METHOD = _make_path(INDEX, DOC_TYPE, ID)
PARAMS = {}
DATA = {"name": "Joe Tester"}
BODY = JSONSerializer().dumps(DATA).encode('utf-8')


def test_connection_default():
    conn = Connection()
    assert conn._nr_host_port == ('localhost', '9200')

def test_connection_host_arg():
    conn = Connection('the_host')
    assert conn._nr_host_port == ('the_host', '9200')

def test_connection_args():
    conn = Connection('the_host', 9999)
    assert conn._nr_host_port == ('the_host', '9999')

def test_connection_kwargs():
    conn = Connection(host='foo', port=8888)
    assert conn._nr_host_port == ('foo', '8888')

def test_urllib3_perform_request():
    app = application()
    with BackgroundTask(app, 'urllib3_perform_request') as transaction:
        conn = Urllib3HttpConnection(ES_SETTINGS['host'], ES_SETTINGS['port'])
        conn.perform_request('POST', METHOD, PARAMS, BODY)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected

def test_requests_perform_request():
    app = application()
    with BackgroundTask(app, 'requests_perform_request') as transaction:
        conn = RequestsHttpConnection(ES_SETTINGS['host'], int(ES_SETTINGS['port']))
        conn.perform_request('POST', METHOD, PARAMS, BODY)

    expected = (ES_SETTINGS['host'], ES_SETTINGS['port'], None)
    assert transaction._nr_datastore_instance_info == expected
