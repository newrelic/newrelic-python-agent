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

import webtest

from testing_support.fixtures import validate_transaction_errors

import cherrypy

class Resource(object):

    exposed = True

    def GET(self):
        return 'GET RESPONSE'

dispatcher = cherrypy.dispatch.MethodDispatcher()

conf = { '/': { 'request.dispatch': dispatcher } }

application = cherrypy.Application(Resource(), '/', conf)
test_application = webtest.TestApp(application)

@validate_transaction_errors(errors=[])
def test_resource_get():
    response = test_application.get('')
    response.mustcontain('GET RESPONSE')

@validate_transaction_errors(errors=[])
def test_resource_not_found():
    response = test_application.post('', status=405)
