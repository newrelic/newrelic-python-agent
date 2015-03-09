try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from ..packages import six

from newrelic.agent import (ObjectProxy, ExternalTrace, wrap_function_wrapper,
        current_transaction, DatastoreTrace)

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

        with ExternalTrace(transaction, 'pyelasticsearch', url, method='GET'):
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

def _extract_index_from_pos1(index_name, *args, **kwargs):
    """Extract the index name which will be the first argument. Returns 'other'
    if the index name is not a string.
    """

    # An index name can sometimes be None or an iterable. In that case we
    # return 'other' because we don't want to consume the iterator just in case
    # it's a generator.

    return index_name if isinstance(index_name, six.string_types) else 'other'

def _extract_index_from_kwarg(*args, **kwargs):
    """Extract the index name from a keyword argument. Return 'other' if the
    index name is not a string.
    """

    # An index name can sometimes be None or an iterable. In that case we
    # return 'other' because we don't want to consume the iterator just in case
    # it's a generator.

    index_name = kwargs.get('index')
    return index_name if isinstance(index_name, six.string_types) else 'other'

_elasticsearch_client_methods = (
    ('bulk_index', _extract_index_from_pos1),
    ('count', _extract_index_from_kwarg),
    ('create_index', _extract_index_from_pos1),
    ('delete', _extract_index_from_pos1),
    ('delete_all', _extract_index_from_pos1),
    ('delete_by_query', _extract_index_from_pos1),
    ('delete_index', _extract_index_from_pos1),
    ('get', _extract_index_from_pos1),
    ('index', _extract_index_from_pos1),
    ('more_like_this', _extract_index_from_pos1),
    ('multi_get', _extract_index_from_kwarg),
    ('percolate', _extract_index_from_pos1),
    ('search', _extract_index_from_kwarg),
    ('update', _extract_index_from_pos1),
)

def wrap_elasticsearch_client_method(module, name, arg_extractor):
    def _nr_wrapper_ElasticSearch_method_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        index = arg_extractor(*args, **kwargs)

        with DatastoreTrace(transaction, product='Elasticsearch',
                target=index, operation=name):
            return wrapped(*args, **kwargs)

    if hasattr(module.ElasticSearch, name):
        wrap_function_wrapper(module.ElasticSearch, name,
                _nr_wrapper_ElasticSearch_method_)

def instrument_pyelasticsearch_client(module):
    # The datastore feature does not need the Instance Names anymore, hence
    # there is no need to patch the ElasticSearch.__init__() method

    # wrap_function_wrapper(module, 'ElasticSearch.__init__',
    # _nr_wrapper_ElasticSearch___init___)

    for name, arg_extractor in _elasticsearch_client_methods:
        wrap_elasticsearch_client_method(module, name, arg_extractor)
