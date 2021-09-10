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
from graphene import Field, Int, List
from graphene import Mutation as GrapheneMutation
from graphene import NonNull, ObjectType, Schema, String, Union


class Author(ObjectType):
    first_name = String()
    last_name = String()


class Book(ObjectType):
    id = Int()
    name = String()
    isbn = String()
    author = Field(Author)
    branch = String()


class Magazine(ObjectType):
    id = Int()
    name = String()
    issue = Int()
    branch = String()


class Item(Union):
    class Meta:
        types = (Book, Magazine)


class Library(ObjectType):
    id = Int()
    branch = String()
    magazine = Field(List(Magazine))
    book = Field(List(Book))


Storage = List(String)


authors = [
    Author(
        first_name="New",
        last_name="Relic",
    ),
    Author(
        first_name="Bob",
        last_name="Smith",
    ),
    Author(
        first_name="Leslie",
        last_name="Jones",
    ),
]

books = [
    Book(
        id=1,
        name="Python Agent: The Book",
        isbn="a-fake-isbn",
        author=authors[0],
        branch="riverside",
    ),
    Book(
        id=2,
        name="Ollies for O11y: A Sk8er's Guide to Observability",
        isbn="a-second-fake-isbn",
        author=authors[1],
        branch="downtown",
    ),
    Book(
        id=3,
        name="[Redacted]",
        isbn="a-third-fake-isbn",
        author=authors[2],
        branch="riverside",
    ),
]

magazines = [
    Magazine(id=1, name="Reli Updates Weekly", issue=1, branch="riverside"),
    Magazine(id=2, name="Reli Updates Weekly", issue=2, branch="downtown"),
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


class StorageAdd(GrapheneMutation):
    class Arguments:
        string = String(required=True)

    string = String()

    def mutate(self, info, string):
        storage.append(string)
        return String(string=string)


class Query(ObjectType):
    library = Field(Library, index=Int(required=True))
    hello = String()
    search = Field(List(Item), contains=String(required=True))
    echo = Field(String, echo=String(required=True))
    storage = Storage
    error = String()

    def resolve_library(self, info, index):
        return libraries[index]

    def resolve_storage(self, info):
        return storage

    def resolve_search(self, info, contains):
        search_books = [b for b in books if contains in b.name]
        search_magazines = [m for m in magazines if contains in m.name]
        return search_books + search_magazines

    def resolve_hello(self, info):
        return "Hello!"

    def resolve_echo(self, info, echo):
        return echo

    def resolve_error(self, info):
        raise RuntimeError("Runtime Error!")

    error_non_null = Field(NonNull(String), resolver=resolve_error)


class Mutation(ObjectType):
    storage_add = StorageAdd.Field()


_target_application = Schema(query=Query, mutation=Mutation, auto_camelcase=False)
