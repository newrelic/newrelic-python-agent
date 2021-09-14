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
from ariadne.wsgi import GraphQL as GraphQLWSGI

schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.graphql")
type_defs = load_schema_from_path(schema_file)


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


mutation = MutationType()


@mutation.field("storage_add")
def mutate(self, info, string):
    storage.append(string)
    return {"string": string}


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
    return storage


@query.field("search")
def resolve_search(self, info, contains):
    search_books = [b for b in books if contains in b["name"]]
    search_magazines = [m for m in magazines if contains in m["name"]]
    return search_books + search_magazines


@query.field("hello")
def resolve_hello(self, info):
    return "Hello!"


@query.field("echo")
def resolve_echo(self, info, echo):
    return echo


@query.field("error_non_null")
@query.field("error")
def resolve_error(self, info):
    raise RuntimeError("Runtime Error!")


_target_application = make_executable_schema(type_defs, query, mutation, item)
_target_asgi_application = GraphQLASGI(_target_application)
_target_wsgi_application = GraphQLWSGI(_target_application)
