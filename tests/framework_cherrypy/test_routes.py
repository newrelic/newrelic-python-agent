import pytest
import sys
import webtest

import cherrypy

is_lt_python30 = sys.version_info[:2] < (3,0)

requires_routes = pytest.mark.skipif(not is_lt_python30,
        reason="The routes package is not yet Python 3 compatible.")

class EndPoint(object):

    def index(self):
        return 'INDEX RESPONSE'

if is_lt_python30:
    dispatcher = cherrypy.dispatch.RoutesDispatcher()
    dispatcher.connect(action='index', name='endpoint', route='/endpoint',
            controller=EndPoint())

    conf = { '/': { 'request.dispatch': dispatcher } }

    application = cherrypy.Application(None, '/', conf)
    test_application = webtest.TestApp(application)

@requires_routes
def test_routes_index():
    response = test_application.get('/endpoint')
    response.mustcontain('INDEX RESPONSE')

@requires_routes
def test_on_index_agent_disabled():
    environ = { 'newrelic.enabled': False }
    response = test_application.get('/endpoint', extra_environ=environ)
    response.mustcontain('INDEX RESPONSE')

@requires_routes
def test_routes_not_found():
    response = test_application.get('/missing', status=404)

@requires_routes
def test_routes_missing_url():
    response = test_application.get('', status=500)
