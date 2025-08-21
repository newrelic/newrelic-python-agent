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

from django.urls import path
from graphene_django.views import GraphQLView


# When New Relic supports async schemas/asgi for graphene-django,
# we can add the schema as an argument like so:
# path("graphql", GraphQLView.as_view(graphiql=False, schema=schema), name="graphql_sync")
# and remove the global schema declaration in settings.py under "GRAPHENE"
urlpatterns = [
    path("graphql", GraphQLView.as_view(graphiql=False), name="graphql_sync"),
]
