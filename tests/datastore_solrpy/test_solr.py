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
