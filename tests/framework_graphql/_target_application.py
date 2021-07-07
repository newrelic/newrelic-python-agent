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
)

libraries = [
    {
        "name": "NYC Public Library",
        "book": [{"name": "A", "author": "B"}, {"name": "C", "author": "D"}],
    },
    {"name": "Portland Public Library", "book": [{"name": "E", "author": "F"}]},
]


def resolve_library(parent, info, index):
    return libraries[index]


Book = GraphQLObjectType(
    "Book",
    {
        "name": GraphQLField(GraphQLString),
        "author": GraphQLField(GraphQLString),
    },
)

Library = GraphQLObjectType(
    "Library",
    {
        "name": GraphQLField(GraphQLString),
        "book": GraphQLField(GraphQLList(Book)),
    },
)


def resolve_hello(root, info):
    return "Hello!"


def resolve_error(root, info):
    raise RuntimeError("Runtime Error!")


try:
    hello_field = GraphQLField(GraphQLString, resolver=resolve_hello)
    library_field = GraphQLField(
        Library,
        resolver=resolve_library,
        args={"index": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
    )
    error_field = GraphQLField(GraphQLString, resolver=resolve_error)
    error_non_null_field = GraphQLField(
        GraphQLNonNull(GraphQLString), resolver=resolve_error
    )
except TypeError:
    hello_field = GraphQLField(GraphQLString, resolve=resolve_hello)
    library_field = GraphQLField(
        Library,
        resolve=resolve_library,
        args={"index": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
    )
    error_field = GraphQLField(GraphQLString, resolve=resolve_error)
    error_non_null_field = GraphQLField(
        GraphQLNonNull(GraphQLString), resolve=resolve_error
    )

query = GraphQLObjectType(
    name="Query",
    fields={
        "hello": hello_field,
        "error": error_field,
        "error_non_null": error_non_null_field,
        "library": library_field,
    },
)

_target_application = GraphQLSchema(query=query)
