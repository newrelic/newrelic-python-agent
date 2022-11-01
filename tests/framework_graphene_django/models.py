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
from django.db.models import CASCADE, ForeignKey, IntegerField, Model, TextField


class Author(Model):
    first_name = TextField()
    last_name = TextField()


class Book(Model):
    id = IntegerField()
    name = TextField()
    isbn = TextField()
    author = ForeignKey(Author, on_delete=CASCADE)
    branch = TextField()


class Magazine(Model):
    id = IntegerField()
    name = TextField()
    issue = IntegerField()
    branch = TextField()


class Library(Model):
    id = IntegerField()
    branch = TextField()
    magazine = ForeignKey(Magazine, on_delete=CASCADE)
    book = ForeignKey(Book, on_delete=CASCADE)
