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

import sqlite3

from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)

from newrelic.api.background_task import background_task

from conftest import ES_VERSION




def _exercise_es_v7(es):
    es.index(index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    es.index(
        index="contacts", doc_type="person", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2
    )
    es.index(index="contacts", doc_type="person", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh("contacts")


def _exercise_es_v8(es):
    es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    es.index(index="contacts", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    es.index(index="contacts", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh(index="contacts")


_exercise_es = _exercise_es_v7 if ES_VERSION < (8, 0, 0) else _exercise_es_v8


@validate_database_duration()
@background_task()
def test_elasticsearch_database_duration(client):
    _exercise_es(client)


@validate_database_duration()
@background_task()
def test_elasticsearch_and_sqlite_database_duration(client):

    # Make Elasticsearch queries

    _exercise_es(client)

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE people (name text, age int)")
    cur.execute("INSERT INTO people VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
