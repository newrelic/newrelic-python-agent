import sqlite3
from elasticsearch import Elasticsearch

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, validate_database_duration)
from testing_support.settings import elasticsearch_settings

from newrelic.agent import background_task

ES_HOST, ES_PORT = elasticsearch_settings()
ES_URL = 'http://%s:%s' % (ES_HOST, ES_PORT)

def _exercise_es(es):
    es.index("contacts", "person",
            {"name": "Joe Tester", "age": 25, "title": "QA Master"}, id=1)
    es.index("contacts", "person",
            {"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    es.index("contacts", "person",
            {"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh('contacts')
    es.index("address", "employee", {"name": "Sherlock",
        "address": "221B Baker Street, London"}, id=1)
    es.index("address", "employee", {"name": "Bilbo",
        "address": "Bag End, Bagshot row, Hobbiton, Shire"}, id=2)
    es.search(index='contacts', q='name:Joe')
    es.search(index='contacts', q='name:jessica')
    es.search(index='address', q='name:Sherlock')
    es.search(index=['contacts', 'address'], q='name:Bilbo')
    es.search(index='contacts,address', q='name:Bilbo')
    es.search(index='*', q='name:Bilbo')
    es.search(q='name:Bilbo')
    es.indices.status()
    es.cat.health()
    es.cluster.health()
    es.nodes.info()
    es.snapshot.status()

# Common Metrics for tests that use _exercise_es().

_test_elasticsearch_scoped_metrics = [
    ('Datastore/statement/Elasticsearch/contacts/index', 3),
    ('Datastore/statement/Elasticsearch/contacts/search', 2),
    ('Datastore/statement/Elasticsearch/address/index', 2),
    ('Datastore/statement/Elasticsearch/address/search', 1),
    ('Datastore/statement/Elasticsearch/_all/search', 2),
    ('Datastore/statement/Elasticsearch/other/search', 2),
    ('Datastore/statement/Elasticsearch/contacts/indices.refresh', 1),
    ('Datastore/statement/Elasticsearch/_all/indices.status', 1),
    ('Datastore/operation/Elasticsearch/cat.health', 1),
    ('Datastore/statement/Elasticsearch/_all/cluster.health', 1),
    ('Datastore/operation/Elasticsearch/nodes.info', 1),
    ('Datastore/operation/Elasticsearch/snapshot.status', 1),
]

_test_elasticsearch_rollup_metrics = [
    ('Datastore/all', 18),
    ('Datastore/allOther', 18),
    ('Datastore/Elasticsearch/all', 18),
    ('Datastore/Elasticsearch/allOther', 18),
    ('Datastore/operation/Elasticsearch/index', 5),
    ('Datastore/operation/Elasticsearch/search', 7),
    ('Datastore/operation/Elasticsearch/indices.refresh', 1),
    ('Datastore/operation/Elasticsearch/indices.status', 1),
    ('Datastore/statement/Elasticsearch/contacts/index', 3),
    ('Datastore/statement/Elasticsearch/contacts/search', 2),
    ('Datastore/statement/Elasticsearch/address/index', 2),
    ('Datastore/statement/Elasticsearch/address/search', 1),
    ('Datastore/statement/Elasticsearch/_all/search', 2),
    ('Datastore/statement/Elasticsearch/other/search', 2),
    ('Datastore/statement/Elasticsearch/contacts/indices.refresh', 1),
    ('Datastore/statement/Elasticsearch/_all/indices.status', 1),
    ('Datastore/operation/Elasticsearch/cat.health', 1),
    ('Datastore/operation/Elasticsearch/cluster.health', 1),
    ('Datastore/statement/Elasticsearch/_all/cluster.health', 1),
    ('Datastore/operation/Elasticsearch/nodes.info', 1),
    ('Datastore/operation/Elasticsearch/snapshot.status', 1),
]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_elasticsearch:test_elasticsearch_operation',
        scoped_metrics=_test_elasticsearch_scoped_metrics,
        rollup_metrics=_test_elasticsearch_rollup_metrics,
        background_task=True)
@background_task()
def test_elasticsearch_operation():
    client = Elasticsearch(ES_URL)
    _exercise_es(client)

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

    cur.execute("CREATE TABLE blah (name text, quantity int)")
    cur.execute("INSERT INTO blah VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
