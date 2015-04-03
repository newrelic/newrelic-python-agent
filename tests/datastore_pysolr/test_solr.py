import os

import pysolr

from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task

_test_solr_search_scoped_metrics = [
        ('Datastore/operation/Solr/search', 1)]

_test_solr_search_rollup_metrics = [
        ('Datastore/all', 1),
        ('Datastore/allOther', 1),
        ('Datastore/Solr/all', 1),
        ('Datastore/Solr/allOther', 1),
        ('Datastore/operation/Solr/search', 1)]

@validate_transaction_metrics('test_solr:test_solr_search',
    scoped_metrics=_test_solr_search_scoped_metrics,
    rollup_metrics=_test_solr_search_rollup_metrics,
    background_task=True)
@background_task()
def test_solr_search():
    s = pysolr.Solr('http://localhost:8983/solr/')
    results = s.search('solr')
