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

import os
import webtest

from ariadne import (
    MutationType,
    QueryType,
    UnionType,
    load_schema_from_path,
    make_executable_schema,
)
from ariadne.wsgi import GraphQL as GraphQLWSGI
from framework_graphql._target_schema_sync import books, magazines, libraries

from testing_support.asgi_testing import AsgiTest
from framework_ariadne.test_application import ARIADNE_VERSION

ariadne_version_tuple = tuple(map(int, ARIADNE_VERSION.split(".")))

if ariadne_version_tuple < (0, 16):
    from ariadne.asgi import GraphQL as GraphQLASGI
elif ariadne_version_tuple >= (0, 16):
    from ariadne.asgi.graphql import GraphQL as GraphQLASGI


schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.graphql")
type_defs = load_schema_from_path(schema_file)

storage = []

mutation = MutationType()



@mutation.field("storage_add")
def resolve_storage_add(self, info, string):
    storage.append(string)
    return string


item = UnionType("Item")


@item.type_resolver
def resolve_type(obj, *args):
    if "isbn" in obj:
        return "Book"
    elif "issue" in obj:  # pylint: disable=R1705
        return "Magazine"

    return None


query = QueryType()


@query.field("library")
def resolve_library(self, info, index):
    return libraries[index]


@query.field("storage")
def resolve_storage(self, info):
    return [storage.pop()]


@query.field("search")
def resolve_search(self, info, contains):
    search_books = [b for b in books if contains in b["name"]]
    search_magazines = [m for m in magazines if contains in m["name"]]
    return search_books + search_magazines


@query.field("hello")
@query.field("error_middleware")
def resolve_hello(self, info):
    return "Hello!"


@query.field("echo")
def resolve_echo(self, info, echo):
    return echo


@query.field("error_non_null")
@query.field("error")
def resolve_error(self, info):
    raise RuntimeError("Runtime Error!")


target_schema = make_executable_schema(type_defs, query, mutation, item)
target_asgi_application = AsgiTest(GraphQLASGI(target_schema))
target_wsgi_application = webtest.TestApp(GraphQLWSGI(target_schema))