import sqlite3

from elasticsearch import Elasticsearch

from newrelic.api.background_task import background_task

from testing_support.db_settings import elasticsearch_settings
from testing_support.validators.validate_database_duration import validate_database_duration

ES_SETTINGS = elasticsearch_settings()[0]
ES_URL = 'http://%s:%s' % (ES_SETTINGS['host'], ES_SETTINGS['port'])

def _exercise_es(es):
    es.index(index="contacts", doc_type="person",
            body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    es.index(index="contacts", doc_type="person",
            body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    es.index(index="contacts", doc_type="person",
            body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh('contacts')

@validate_database_duration()
@background_task()
def test_elasticsearch_database_duration():
    client = Elasticsearch(ES_URL)
    _exercise_es(client)

@validate_database_duration()
@background_task()
def test_elasticsearch_and_sqlite_database_duration():

    # Make Elasticsearch queries

    client = Elasticsearch(ES_URL)
    _exercise_es(client)

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE people (name text, age int)")
    cur.execute("INSERT INTO people VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
