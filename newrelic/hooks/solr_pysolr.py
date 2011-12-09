import newrelic.api.solr_trace

def instrument(module):

    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.search', 'pysolr', 'query')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.more_like_this', 'pysolr', 'query')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.suggest_terms', 'pysolr', 'query')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.add', 'pysolr', 'add')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.delete', 'pysolr', 'delete')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.commit', 'pysolr', 'commit')
    newrelic.api.solr_trace.wrap_solr_trace(
            module, 'Solr.delete', 'pysolr', 'optimize')
