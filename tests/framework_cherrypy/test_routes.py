import pytest
import sys
import webtest

from testing_support.fixtures import validate_transaction_errors

import cherrypy

class EndPoint(object):

    def index(self):
        return 'INDEX RESPONSE'

dispatcher = cherrypy.dispatch.RoutesDispatcher()
dispatcher.connect(action='index', name='endpoint', route='/endpoint',
            controller=EndPoint())

conf = { '/': { 'request.dispatch': dispatcher } }

application = cherrypy.Application(None, '/', conf)
test_application = webtest.TestApp(application)

@validate_transaction_errors(errors=[])
def test_routes_index():
    response = test_application.get('/endpoint')
    response.mustcontain('INDEX RESPONSE')

@validate_transaction_errors(errors=[])
def test_on_index_agent_disabled():
    environ = { 'newrelic.enabled': False }
    response = test_application.get('/endpoint', extra_environ=environ)
    response.mustcontain('INDEX RESPONSE')

@validate_transaction_errors(errors=[])
def test_routes_not_found():
    response = test_application.get('/missing', status=404)
