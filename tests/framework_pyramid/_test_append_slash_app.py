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

from pyramid.response import Response
from pyramid.view import view_config, notfound_view_config
from pyramid.config import Configurator
import pyramid.httpexceptions as exc


@view_config(route_name='home')
def home_view(request):
    return Response('<p>INDEX RESPONSE</p>')

@notfound_view_config(append_slash=True)
def not_found(request):
    return Response('<p>NOT FOUND</p>', status='404 Not Found')

config = Configurator()
config.add_route('home', '/')
config.scan()

application = config.make_wsgi_app()

_test_application = webtest.TestApp(application)
