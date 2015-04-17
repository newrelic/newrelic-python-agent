from solr import SolrConnection

SOLR_URL = 'http://localhost:8983/solr'

def _exercise_solr(solr):
    print "Before add"
    print solr.add_many([
        {"id": "doc_1", "title": "A test document"},
        {"id": "doc_2", "title": "The Banana: Tasty or Dangerous?"},
        ])
    solr.commit()
    print "After add"

    print solr.query('title:banana')
    solr.delete('id:doc_1')

    solr.commit()
    # Delete all documents.
    solr.delete('*:*')
    solr.commit()

_test_solr_search_scoped_metrics = [
        ('Datastore/operation/Solr/add', 1),
        ('Datastore/operation/Solr/delete', 2),
        ('Datastore/operation/Solr/query', 1)]

_test_solr_search_rollup_metrics = [
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Solr/all', 4),
        ('Datastore/Solr/allOther', 4),
        ('Datastore/operation/Solr/add', 1),
        ('Datastore/operation/Solr/query', 1),
        ('Datastore/operation/Solr/delete', 2)]

s = SolrConnection(SOLR_URL)
#import pdb; pdb.set_trace()
_exercise_solr(s)
