from solr import SolrConnection

from testing_support.fixtures import validate_transaction_metrics
from testing_support.settings import solr_settings

from newrelic.api.background_task import background_task

SOLR_HOST, SOLR_PORT = solr_settings()
SOLR_URL = 'http://%s:%s/solr/collection' % (SOLR_HOST, SOLR_PORT)

def _exercise_solr(solr):
    solr.add_many([
        {"id": "doc_1"},
        {"id": "doc_2"},
        ])
    solr.commit()
    solr.query('id:doc_1').results
    solr.delete('id:doc_1')
    solr.commit()

_test_solr_search_scoped_metrics = [
        ('Datastore/operation/Solr/add_many', 1),
        ('Datastore/operation/Solr/delete', 1),
        ('Datastore/operation/Solr/commit', 2),
        ('Datastore/operation/Solr/query', 1)]

_test_solr_search_rollup_metrics = [
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Solr/all', 5),
        ('Datastore/Solr/allOther', 5),
        ('Datastore/operation/Solr/add_many', 1),
        ('Datastore/operation/Solr/query', 1),
        ('Datastore/operation/Solr/commit', 2),
        ('Datastore/operation/Solr/delete', 1)]

@validate_transaction_metrics('test_solr:test_solr_search',
    scoped_metrics=_test_solr_search_scoped_metrics,
    rollup_metrics=_test_solr_search_rollup_metrics,
    background_task=True)
@background_task()
def test_solr_search():
    s = SolrConnection(SOLR_URL)
    _exercise_solr(s)
