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

from ariadne import (
    MutationType,
    QueryType,
    UnionType,
    load_schema_from_path,
    make_executable_schema,
)
from ariadne.asgi import GraphQL as GraphQLASGI
from framework_graphql._target_schema_sync import books, magazines, libraries

from testing_support.asgi_testing import AsgiTest

schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.graphql")
type_defs = load_schema_from_path(schema_file)

storage = []

mutation = MutationType()


@mutation.field("storage_add")
async def resolve_storage_add(self, info, string):
    storage.append(string)
    return string


item = UnionType("Item")


@item.type_resolver
async def resolve_type(obj, *args):
    if "isbn" in obj:
        return "Book"
    elif "issue" in obj:  # pylint: disable=R1705
        return "Magazine"

    return None


query = QueryType()


@query.field("library")
async def resolve_library(self, info, index):
    return libraries[index]


@query.field("storage")
async def resolve_storage(self, info):
    return [storage.pop()]


@query.field("search")
async def resolve_search(self, info, contains):
    search_books = [b for b in books if contains in b["name"]]
    search_magazines = [m for m in magazines if contains in m["name"]]
    return search_books + search_magazines


@query.field("hello")
@query.field("error_middleware")
async def resolve_hello(self, info):
    return "Hello!"


@query.field("echo")
async def resolve_echo(self, info, echo):
    return echo


@query.field("error_non_null")
@query.field("error")
async def resolve_error(self, info):
    raise RuntimeError("Runtime Error!")


target_schema = make_executable_schema(type_defs, query, mutation, item)
target_asgi_application = AsgiTest(GraphQLASGI(target_schema))
