from solr import SolrConnection

from testing_support.fixtures import validate_transaction_metrics
from testing_support.db_settings import solr_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = solr_settings()[0]
SOLR_HOST = DB_SETTINGS["host"]
SOLR_PORT = DB_SETTINGS["port"]
SOLR_URL = 'http://%s:%s/solr/collection' % (DB_SETTINGS["host"], DB_SETTINGS["port"])

def _exercise_solr(solr):
    # Construct document names within namespace
    documents = ["pysolr_doc_1", "pysolr_doc_2"]
    documents = [x + "_" + DB_SETTINGS["namespace"] for x in documents]

    solr.add_many([{"id": x} for x in documents])
    solr.commit()
    solr.query('id:%s' % documents[0]).results
    solr.delete('id:*_%s' % DB_SETTINGS["namespace"])
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
