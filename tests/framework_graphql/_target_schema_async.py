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

from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    GraphQLUnionType,
)

from ._target_schema_sync import books, libraries, magazines

storage = []


async def resolve_library(parent, info, index):
    return libraries[index]


async def resolve_storage_add(parent, info, string):
    storage.append(string)
    return string


async def resolve_storage(parent, info):
    return [storage.pop()]


async def resolve_search(parent, info, contains):
    search_books = [b for b in books if contains in b["name"]]
    search_magazines = [m for m in magazines if contains in m["name"]]
    return search_books + search_magazines


Author = GraphQLObjectType(
    "Author",
    {
        "first_name": GraphQLField(GraphQLString),
        "last_name": GraphQLField(GraphQLString),
    },
)

Book = GraphQLObjectType(
    "Book",
    {
        "id": GraphQLField(GraphQLInt),
        "name": GraphQLField(GraphQLString),
        "isbn": GraphQLField(GraphQLString),
        "author": GraphQLField(Author),
        "branch": GraphQLField(GraphQLString),
    },
)

Magazine = GraphQLObjectType(
    "Magazine",
    {
        "id": GraphQLField(GraphQLInt),
        "name": GraphQLField(GraphQLString),
        "issue": GraphQLField(GraphQLInt),
        "branch": GraphQLField(GraphQLString),
    },
)


Library = GraphQLObjectType(
    "Library",
    {
        "id": GraphQLField(GraphQLInt),
        "branch": GraphQLField(GraphQLString),
        "book": GraphQLField(GraphQLList(Book)),
        "magazine": GraphQLField(GraphQLList(Magazine)),
    },
)

Storage = GraphQLList(GraphQLString)


async def resolve_hello(root, info):
    return "Hello!"


async def resolve_echo(root, info, echo):
    return echo


async def resolve_error(root, info):
    raise RuntimeError("Runtime Error!")


hello_field = GraphQLField(GraphQLString, resolver=resolve_hello)
library_field = GraphQLField(
    Library,
    resolver=resolve_library,
    args={"index": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
)
search_field = GraphQLField(
    GraphQLList(GraphQLUnionType("Item", (Book, Magazine), resolve_type=resolve_search)),
    args={"contains": GraphQLArgument(GraphQLNonNull(GraphQLString))},
)
echo_field = GraphQLField(
    GraphQLString,
    resolver=resolve_echo,
    args={"echo": GraphQLArgument(GraphQLNonNull(GraphQLString))},
)
storage_field = GraphQLField(
    Storage,
    resolver=resolve_storage,
)
storage_add_field = GraphQLField(
    GraphQLString,
    resolver=resolve_storage_add,
    args={"string": GraphQLArgument(GraphQLNonNull(GraphQLString))},
)
error_field = GraphQLField(GraphQLString, resolver=resolve_error)
error_non_null_field = GraphQLField(GraphQLNonNull(GraphQLString), resolver=resolve_error)
error_middleware_field = GraphQLField(GraphQLString, resolver=resolve_hello)

query = GraphQLObjectType(
    name="Query",
    fields={
        "hello": hello_field,
        "library": library_field,
        "search": search_field,
        "echo": echo_field,
        "storage": storage_field,
        "error": error_field,
        "error_non_null": error_non_null_field,
        "error_middleware": error_middleware_field,
    },
)

mutation = GraphQLObjectType(
    name="Mutation",
    fields={
        "storage_add": storage_add_field,
    },
)

target_schema = GraphQLSchema(query=query, mutation=mutation)
