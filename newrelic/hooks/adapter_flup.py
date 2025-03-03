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


def wrap_wsgi_application_entry_point(server, application, *args, **kwargs):
    application = newrelic.api.wsgi_application.WSGIApplicationWrapper(application)
    args = [server, application] + list(args)
    return (args, kwargs)


def instrument_flup_server_cgi(module):
    newrelic.api.in_function.wrap_in_function(module, "WSGIServer.__init__", wrap_wsgi_application_entry_point)


def instrument_flup_server_ajp_base(module):
    newrelic.api.in_function.wrap_in_function(module, "BaseAJPServer.__init__", wrap_wsgi_application_entry_point)


def instrument_flup_server_fcgi_base(module):
    newrelic.api.in_function.wrap_in_function(module, "BaseFCGIServer.__init__", wrap_wsgi_application_entry_point)


def instrument_flup_server_scgi_base(module):
    newrelic.api.in_function.wrap_in_function(module, "BaseSCGIServer.__init__", wrap_wsgi_application_entry_point)
