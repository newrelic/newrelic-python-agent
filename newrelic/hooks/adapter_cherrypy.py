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

import newrelic.api.in_function
import newrelic.api.wsgi_application


def instrument_cherrypy_wsgiserver(module):
    def wrap_wsgi_application_entry_point(server, bind_addr, wsgi_app, *args, **kwargs):
        application = newrelic.api.wsgi_application.WSGIApplicationWrapper(wsgi_app)
        args = [server, bind_addr, application] + list(args)
        return (args, kwargs)

    newrelic.api.in_function.wrap_in_function(module, "CherryPyWSGIServer.__init__", wrap_wsgi_application_entry_point)
