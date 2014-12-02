try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from newrelic.agent import (ObjectProxy, ExternalTrace, wrap_function_wrapper,
        current_transaction)

from newrelic.api.datastore_trace import DatastoreTrace

# List of methods in the pyelasticsearch module that has 'index' as a kwarg.
kw_index_methods = ['search', 'multi_get', 'count']

# List of methods in the pyelasticsearch module that has 'index' as a
# positional arg.
pos_index_methods = ['get', 'delete', 'delete_all', 'delete_by_query',
'delete_index', 'create_index', 'bulk_index', 'more_like_this', 'percolate',
'update', 'index']


def extract_netloc(url):
    details = urlparse.urlparse(url)

    hostname = details.hostname or 'unknown'

    try:
        scheme = details.scheme.lower()
        port = details.port
    except Exception:
        scheme = None
        port = None

    if (scheme, port) in (('http', 80), ('https', 443)):
        port = None

    netloc = port and ('%s:%s' % (hostname, port)) or hostname

    return netloc

class RequestsSessionObjectProxy(ObjectProxy):
    """A class that proxies all attribute access to the underlying class. But
    overrides the http methods get, post, delete and put to grab the url to
    extract the hostname.

    """
    def post(self, *args, **kwargs):
        def _bind_params(url, *args, **kwargs):
            return url

        transaction = current_transaction()

        if transaction is None:
            return self.__wrapped__.post(*args, **kwargs)

        url = _bind_params(*args, **kwargs)

        node = transaction.active_node()

        if isinstance(node, DatastoreTrace):
            node.instance = extract_netloc(url)

        with ExternalTrace(transaction, 'pyelasticsearch', url, method='POST'):
            return self.__wrapped__.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        def _bind_params(url, *args, **kwargs):
            return url

        transaction = current_transaction()

        if transaction is None:
            return self.__wrapped__.get(*args, **kwargs)

        url = _bind_params(*args, **kwargs)

        node = transaction.active_node()

        if isinstance(node, DatastoreTrace):
            node.instance = extract_netloc(url)

        return self.__wrapped__.get(*args, **kwargs)

    def put(self, *args, **kwargs):
        def _bind_params(url, *args, **kwargs):
            return url

        transaction = current_transaction()

        if transaction is None:
            return self.__wrapped__.put(*args, **kwargs)

        url = _bind_params(*args, **kwargs)

        node = transaction.active_node()

        if isinstance(node, DatastoreTrace):
            node.instance = extract_netloc(url)

        with ExternalTrace(transaction, 'pyelasticsearch', url, method='PUT'):
            return self.__wrapped__.put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        def _bind_params(url, *args, **kwargs):
            return url

        transaction = current_transaction()

        if transaction is None:
            return self.__wrapped__.delete(*args, **kwargs)

        url = _bind_params(*args, **kwargs)

        node = transaction.active_node()

        if isinstance(node, DatastoreTrace):
            node.instance = extract_netloc(url)

        with ExternalTrace(transaction, 'pyelasticsearch', url,
                method='DELETE'):
            return self.__wrapped__.delete(*args, **kwargs)

def _nr_wrapper_ElasticSearch___init___(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance.session = RequestsSessionObjectProxy(instance.session)
    return result

def _nr_wrapper_ElasticSearch_kw_index_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(*args, **kwargs):
        return kwargs.get('index', 'other')

    index = _bind_params(*args, **kwargs)

    # with DatastoreTrace(transaction, 'ElasticSearch', index,
    # wrapped.__name__, 'unknown') as tracer:
    with DatastoreTrace(transaction, 'Elasticsearch', index, wrapped.__name__):
        return wrapped(*args, **kwargs)

def _nr_wrapper_ElasticSearch_pos_index_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(index, *args, **kwargs):
        return index

    index = _bind_params(*args, **kwargs)

    # with DatastoreTrace(transaction, 'Elasticsearch', index,
    # wrapped.__name__, 'unknown') as tracer:
    with DatastoreTrace(transaction, 'Elasticsearch', index, wrapped.__name__):
        return wrapped(*args, **kwargs)

def instrument_pyelasticsearch_client(module):

    # The datastore feature does not need the Instance Names anymore, hence
    # there is no need to patch the ElasticSearch.__init__() method

    # wrap_function_wrapper(module, 'ElasticSearch.__init__',
    # _nr_wrapper_ElasticSearch___init___)

    for method in kw_index_methods:
        if hasattr(module.ElasticSearch, method):
            wrap_function_wrapper(module, 'ElasticSearch.%s' % method,
                    _nr_wrapper_ElasticSearch_kw_index_)

    for method in pos_index_methods:
        if hasattr(module.ElasticSearch, method):
            wrap_function_wrapper(module, 'ElasticSearch.%s' % method,
                    _nr_wrapper_ElasticSearch_pos_index_)
