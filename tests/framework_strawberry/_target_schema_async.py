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

from typing import List
import strawberry.mutation
import strawberry.type
from strawberry import Schema, field
from strawberry.asgi import GraphQL
from strawberry.schema.config import StrawberryConfig
from strawberry.types.types import Optional
from testing_support.asgi_testing import AsgiTest

from ._target_schema_sync import Library, Item, Storage, books, magazines, libraries


storage = []


async def resolve_hello():
    return "Hello!"


async def resolve_echo(echo: str):
    return echo


async def resolve_library(index: int):
    return libraries[index]


async def resolve_storage_add(string: str):
    storage.append(string)
    return string


async def resolve_storage():
    return [storage.pop()]


async def resolve_error():
    raise RuntimeError("Runtime Error!")


async def resolve_search(contains: str):
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
