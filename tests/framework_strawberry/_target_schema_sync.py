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

from __future__ import annotations

from typing import List, Optional, Union

import strawberry

try:
    import strawberry.mutation
except ImportError:
    import strawberry.types.mutation

from strawberry import Schema, field
from strawberry.asgi import GraphQL
from strawberry.schema.config import StrawberryConfig
from testing_support.asgi_testing import AsgiTest


@strawberry.type
class Author:
    first_name: str
    last_name: str


@strawberry.type
class Book:
    id: int
    name: str
    isbn: str
    author: Author
    branch: str


@strawberry.type
class Magazine:
    id: int
    name: str
    issue: int
    branch: str


@strawberry.type
class Library:
    id: int
    branch: str
    magazine: List[Magazine]
    book: List[Book]


Item = Union[Book, Magazine]
Storage = List[str]


authors = [
    Author(first_name="New", last_name="Relic"),
    Author(first_name="Bob", last_name="Smith"),
    Author(first_name="Leslie", last_name="Jones"),
]

books = [
    Book(id=1, name="Python Agent: The Book", isbn="a-fake-isbn", author=authors[0], branch="riverside"),
    Book(
        id=2,
        name="Ollies for O11y: A Sk8er's Guide to Observability",
        isbn="a-second-fake-isbn",
        author=authors[1],
        branch="downtown",
    ),
    Book(id=3, name="[Redacted]", isbn="a-third-fake-isbn", author=authors[2], branch="riverside"),
]

magazines = [
    Magazine(id=1, name="Reli Updates Weekly", issue=1, branch="riverside"),
    Magazine(id=2, name="Reli: The Forgotten Years", issue=2, branch="downtown"),
    Magazine(id=3, name="Node Weekly", issue=1, branch="riverside"),
]


libraries = ["riverside", "downtown"]
libraries = [
    Library(
        id=i + 1,
        branch=branch,
        magazine=[m for m in magazines if m.branch == branch],
        book=[b for b in books if b.branch == branch],
    )
    for i, branch in enumerate(libraries)
]

storage = []


def resolve_hello():
    return "Hello!"


def resolve_echo(echo: str):
    return echo


def resolve_library(index: int):
    return libraries[index]


def resolve_storage_add(string: str):
    storage.append(string)
    return string


def resolve_storage():
    return [storage.pop()]


def resolve_error():
    raise RuntimeError("Runtime Error!")


def resolve_search(contains: str):
    search_books = [b for b in books if contains in b.name]
    search_magazines = [m for m in magazines if contains in m.name]
    return search_books + search_magazines


@strawberry.type
class Query:
    library: Library = field(resolver=resolve_library)
    hello: str = field(resolver=resolve_hello)
    search: List[Item] = field(resolver=resolve_search)
    echo: str = field(resolver=resolve_echo)
    storage: Storage = field(resolver=resolve_storage)
    error: Optional[str] = field(resolver=resolve_error)
    error_non_null: str = field(resolver=resolve_error)


@strawberry.type
class Mutation:
    storage_add: str = strawberry.mutation(resolver=resolve_storage_add)


target_schema = Schema(query=Query, mutation=Mutation, config=StrawberryConfig(auto_camel_case=False))
target_asgi_application = AsgiTest(GraphQL(target_schema))
