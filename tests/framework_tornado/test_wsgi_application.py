import webtest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

import tornado.web
import tornado.wsgi

from newrelic.packages import six

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("GET RESPONSE")
    def post(self):
        self.write("POST RESPONSE")

application = tornado.wsgi.WSGIApplication([
    (r"/get", MainHandler),
    (r"/post", MainHandler),
])

test_application = webtest.TestApp(application)

_test_wsgi_application_main_get_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/tornado.wsgi:WSGIApplication.__call__', 1),
        ('Function/tornado.httputil:parse_body_arguments', 1),
        ('Python/Tornado/Request/Process', 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.prepare',
            py3='Function/tornado.web:RequestHandler.prepare'), 1),
        ('Function/test_wsgi_application:MainHandler.get', 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.finish',
            py3='Function/tornado.web:RequestHandler.finish'), 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.on_finish',
            py3='Function/tornado.web:RequestHandler.on_finish'), 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_wsgi_application:MainHandler.get',
        scoped_metrics=_test_wsgi_application_main_get_scoped_metrics)
def test_wsgi_application_main_get():
    response = test_application.get('/get')
    response.mustcontain('GET RESPONSE')

_test_wsgi_application_main_post_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/tornado.wsgi:WSGIApplication.__call__', 1),
        ('Function/tornado.httputil:parse_body_arguments', 1),
        ('Python/Tornado/Request/Process', 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.prepare',
            py3='Function/tornado.web:RequestHandler.prepare'), 1),
        ('Function/test_wsgi_application:MainHandler.post', 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.finish',
            py3='Function/tornado.web:RequestHandler.finish'), 1),
        (select_python_version(
            py2='Function/test_wsgi_application:MainHandler.on_finish',
            py3='Function/tornado.web:RequestHandler.on_finish'), 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_wsgi_application:MainHandler.post',
        scoped_metrics=_test_wsgi_application_main_post_scoped_metrics)
def test_wsgi_application_main_post():
    response = test_application.post('/post', params={'a': 'b'})
    response.mustcontain('POST RESPONSE')
