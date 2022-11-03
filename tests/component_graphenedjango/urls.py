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
    from django.conf.urls.defaults import path
except ImportError:
    try:
        from django.conf.urls import path
    except ImportError:
        from django.urls import path

from django.views.decorators.csrf import csrf_exempt
from framework_graphene._target_schema_sync import target_schema
from graphene_django.views import GraphQLView

urlpatterns = [
    path("", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=target_schema)), name="graphql"),
]
