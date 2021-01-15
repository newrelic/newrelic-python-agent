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

try:
    from django.conf.urls import url, include
except ImportError:
    try:
        from django.conf.urls.defaults import url, include
    except ImportError:
        from django.urls import re_path as url, include

from tastypie.api import Api

import views

from api import SimpleResource

simple_resource = SimpleResource()

urlpatterns = [
    url(r'^index/$', views.index, name='index'),
    url(r'^api/v1/', include(simple_resource.urls)),
]

v2_api = Api(api_name='v2')
v2_api.register(SimpleResource())

urlpatterns += [
    url(r'^api/', include(v2_api.urls)),
]
