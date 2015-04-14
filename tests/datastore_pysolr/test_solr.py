from pysolr import Solr

from testing_support.fixtures import validate_transaction_metrics
from testing_support.settings import solr_settings

from newrelic.agent import background_task

SOLR_HOST, SOLR_PORT = solr_settings()
SOLR_URL = 'http://%s:%s' % (SOLR_HOST, SOLR_PORT)

def _exercise_solr(solr):
    solr.add([
        {"id": "doc_1", "title": "A test document"},
        {"id": "doc_2", "title": "The Banana: Tasty or Dangerous?"},
        ])

    solr.search('banana')
    solr.delete(id='doc_1')

    # Delete all documents.
    solr.delete(q='*:*')

_test_solr_search_scoped_metrics = [
        ('Datastore/operation/Solr/add', 1),
        ('Datastore/operation/Solr/delete', 2),
        ('Datastore/operation/Solr/search', 1)]

_test_solr_search_rollup_metrics = [
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Solr/all', 4),
        ('Datastore/Solr/allOther', 4),
        ('Datastore/operation/Solr/add', 1),
        ('Datastore/operation/Solr/search', 1),
        ('Datastore/operation/Solr/delete', 2)]

@validate_transaction_metrics('test_solr:test_solr_search',
    scoped_metrics=_test_solr_search_scoped_metrics,
    rollup_metrics=_test_solr_search_rollup_metrics,
    background_task=True)
@background_task()
def test_solr_search():
    s = Solr('http://localhost:8983/solr/')
    _exercise_solr(s)
