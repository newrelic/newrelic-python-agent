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
import webtest

from newrelic.packages import six

from testing_support.fixtures import validate_transaction_errors

import cherrypy

is_ge_cherrypy32 = (tuple(map(int,
        cherrypy.__version__.split('.')[:2])) >= (3,2))

requires_cherrypy32 = pytest.mark.skipif(not is_ge_cherrypy32,
        reason="The dispatch mechanism was only added in CherryPy 3.2.")

class Resource(object):

    def _cp_dispatch(self, vpath):
        raise RuntimeError('dispatch error')

if is_ge_cherrypy32:
    dispatcher = cherrypy.dispatch.MethodDispatcher()

    conf = { '/': { 'request.dispatch': dispatcher } }

    application = cherrypy.Application(Resource(), '/', conf)
    test_application = webtest.TestApp(application)

if six.PY3:
    _test_dispatch_exception_errors = ['builtins:RuntimeError']
else:
    _test_dispatch_exception_errors = ['exceptions:RuntimeError']

@requires_cherrypy32
@validate_transaction_errors(errors=_test_dispatch_exception_errors)
def test_dispatch_exception():
    response = test_application.get('/sub/a/b', status=500)
