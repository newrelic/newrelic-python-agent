import httplib2

from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task

_test_httplib2_http_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_http_connection_request',
        scoped_metrics=_test_httplib2_http_request_scoped_metrics,
        rollup_metrics=_test_httplib2_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_http_connection_request():
    connection = httplib2.HTTPConnectionWithTimeout('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()

_test_httplib2_https_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_https_connection_request',
        scoped_metrics=_test_httplib2_https_request_scoped_metrics,
        rollup_metrics=_test_httplib2_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_https_connection_request():
    connection = httplib2.HTTPSConnectionWithTimeout('www.example.com', 443)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()
_test_httplib2_http_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_http_request',
        scoped_metrics=_test_httplib2_http_request_scoped_metrics,
        rollup_metrics=_test_httplib2_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_http_request():
    connection = httplib2.Http()
    response, content = connection.request('http://www.example.com', 'GET')
