import cherrypy.wsgiserver


def wsgi_test_app(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return ['Hello world!']

def test_wsgi_app_positional_args():
    server = cherrypy.wsgiserver.CherryPyWSGIServer(('0.0.0.0', 8070),
            wsgi_test_app)

def test_wsgi_app_keyword_args():
    server = cherrypy.wsgiserver.CherryPyWSGIServer(bind_addr=('0.0.0.0', 8070),
            wsgi_app=wsgi_test_app)
