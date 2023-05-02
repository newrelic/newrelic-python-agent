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

authors = [
    {
        "first_name": "New",
        "last_name": "Relic",
    },
    {
        "first_name": "Bob",
        "last_name": "Smith",
    },
    {
        "first_name": "Leslie",
        "last_name": "Jones",
    },
]

books = [
    {
        "id": 1,
        "name": "Python Agent: The Book",
        "isbn": "a-fake-isbn",
        "author": authors[0],
        "branch": "riverside",
    },
    {
        "id": 2,
        "name": "Ollies for O11y: A Sk8er's Guide to Observability",
        "isbn": "a-second-fake-isbn",
        "author": authors[1],
        "branch": "downtown",
    },
    {
        "id": 3,
        "name": "[Redacted]",
        "isbn": "a-third-fake-isbn",
        "author": authors[2],
        "branch": "riverside",
    },
]

magazines = [
    {"id": 1, "name": "Reli Updates Weekly", "issue": 1, "branch": "riverside"},
    {"id": 2, "name": "Reli Updates Weekly", "issue": 2, "branch": "downtown"},
    {"id": 3, "name": "Node Weekly", "issue": 1, "branch": "riverside"},
]


libraries = ["riverside", "downtown"]
libraries = [
    {
        "id": i + 1,
        "branch": branch,
        "magazine": [m for m in magazines if m["branch"] == branch],
        "book": [b for b in books if b["branch"] == branch],
    }
    for i, branch in enumerate(libraries)
]

storage = []


def resolve_library(parent, info, index):
    return libraries[index]


def resolve_storage_add(parent, info, string):
    storage.append(string)
    return string


def resolve_storage(parent, info):
    return storage


def resolve_search(parent, info, contains):
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


def resolve_hello(root, info):
    return "Hello!"


def resolve_echo(root, info, echo):
    return echo


def resolve_error(root, info):
    raise RuntimeError("Runtime Error!")


try:
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
        Storage,
        resolver=resolve_storage_add,
        args={"string": GraphQLArgument(GraphQLNonNull(GraphQLString))},
    )
    error_field = GraphQLField(GraphQLString, resolver=resolve_error)
    error_non_null_field = GraphQLField(GraphQLNonNull(GraphQLString), resolver=resolve_error)
    error_middleware_field = GraphQLField(GraphQLString, resolver=resolve_hello)
except TypeError:
    hello_field = GraphQLField(GraphQLString, resolve=resolve_hello)
    library_field = GraphQLField(
        Library,
        resolve=resolve_library,
        args={"index": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
    )
    search_field = GraphQLField(
        GraphQLList(GraphQLUnionType("Item", (Book, Magazine), resolve_type=resolve_search)),
        args={"contains": GraphQLArgument(GraphQLNonNull(GraphQLString))},
    )
    echo_field = GraphQLField(
        GraphQLString,
        resolve=resolve_echo,
        args={"echo": GraphQLArgument(GraphQLNonNull(GraphQLString))},
    )
    storage_field = GraphQLField(
        Storage,
        resolve=resolve_storage,
    )
    storage_add_field = GraphQLField(
        GraphQLString,
        resolve=resolve_storage_add,
        args={"string": GraphQLArgument(GraphQLNonNull(GraphQLString))},
    )
    error_field = GraphQLField(GraphQLString, resolve=resolve_error)
    error_non_null_field = GraphQLField(GraphQLNonNull(GraphQLString), resolve=resolve_error)
    error_middleware_field = GraphQLField(GraphQLString, resolve=resolve_hello)

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

_target_application = GraphQLSchema(query=query, mutation=mutation)
