import sqlite3
from pyelasticsearch import ElasticSearch

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
    es.refresh('contacts')
    es.index("address", "employee", {"name": "Sherlock",
        "address": "221B Baker Street, London"}, id=1)
    es.index("address", "employee", {"name": "Bilbo",
        "address": "Bag End, Bagshot row, Hobbiton, Shire"}, id=2)
    es.search('name:Joe', index='contacts')
    es.search('name:jessica', index='contacts')
    es.search('name:Sherlock', index='address')
    es.search('name:Bilbo', index=['contacts', 'address'])

# Common Metrics for tests that use _exercise_es().

_test_pyelasticsearch_scoped_metrics = [
        ('Datastore/statement/Elasticsearch/contacts/index', 3),
        ('Datastore/statement/Elasticsearch/contacts/search', 2),
        ('Datastore/statement/Elasticsearch/address/search', 1),
        ]

_test_pyelasticsearch_rollup_metrics = [
        ('Datastore/all', 10),
        ('Datastore/allOther', 10),
        ('Datastore/Elasticsearch/all', 10),
        ('Datastore/Elasticsearch/allOther', 10),
        ('Datastore/operation/Elasticsearch/index', 5),
        ('Datastore/operation/Elasticsearch/search', 4),
        ('Datastore/statement/Elasticsearch/contacts/index', 3),
        ('Datastore/statement/Elasticsearch/contacts/search', 2),
        ('Datastore/statement/Elasticsearch/address/index', 2),
        ('Datastore/statement/Elasticsearch/address/search', 1),
        ('Datastore/statement/Elasticsearch/other/search', 1),
        ('Datastore/operation/Elasticsearch/send_request', 1),  # refresh()
        ]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_pyelasticsearch:test_pyelasticsearch_operation',
        scoped_metrics=_test_pyelasticsearch_scoped_metrics,
        rollup_metrics=_test_pyelasticsearch_rollup_metrics,
        background_task=True)
@background_task()
def test_pyelasticsearch_operation():
    client = ElasticSearch(ES_URL)
    _exercise_es(client)

@validate_database_duration()
@background_task()
def test_elasticsearch_database_duration():
    client = ElasticSearch(ES_URL)
    _exercise_es(client)

@validate_database_duration()
@background_task()
def test_elasticsearch_and_sqlite_database_duration():

    # Make ElasticSearch queries

    client = ElasticSearch(ES_URL)
    _exercise_es(client)

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE blah (name text, quantity int)")
    cur.execute("INSERT INTO blah VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
