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
from promise import promisify

from ._target_schema_sync import Author, Book, Magazine, Item, Library, Storage, authors, books, magazines, libraries


storage = []


@promisify
def resolve_library(self, info, index):
    return libraries[index]

@promisify
def resolve_storage(self, info):
    return [storage.pop()]

@promisify
def resolve_search(self, info, contains):
    search_books = [b for b in books if contains in b.name]
    search_magazines = [m for m in magazines if contains in m.name]
    return search_books + search_magazines

@promisify
def resolve_hello(self, info):
    return "Hello!"

@promisify
def resolve_echo(self, info, echo):
    return echo

@promisify
def resolve_error(self, info):
    raise RuntimeError("Runtime Error!")

@promisify
def resolve_storage_add(self, info, string):
    storage.append(string)
    return StorageAdd(string=string)


class StorageAdd(GrapheneMutation):
    class Arguments:
        string = String(required=True)

    string = String()
    mutate = resolve_storage_add


class Query(ObjectType):
    library = Field(Library, index=Int(required=True), resolver=resolve_library)
    hello = String(resolver=resolve_hello)
    search = Field(List(Item), contains=String(required=True), resolver=resolve_search)
    echo = Field(String, echo=String(required=True), resolver=resolve_echo)
    storage = Field(Storage, resolver=resolve_storage)
    error = String(resolver=resolve_error)
    error_non_null = Field(NonNull(String), resolver=resolve_error)
    error_middleware = String(resolver=resolve_hello)


class Mutation(ObjectType):
    storage_add = StorageAdd.Field()


target_schema = Schema(query=Query, mutation=Mutation, auto_camelcase=False)
