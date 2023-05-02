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
import sys
import webtest

from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics

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

@validate_code_level_metrics("test_routes.EndPoint", "index")
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
