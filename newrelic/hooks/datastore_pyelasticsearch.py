from ..packages import six

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        DatastoreTrace)

def _extract_index_from_pos1(index, *args, **kwargs):
    """Extract the index name which will be the first argument. Returns 'other'
    if the index name is not a string.
    """

    # An index name can sometimes be None or an iterable. In that case we
    # return 'other' because we don't want to consume the iterator just in case
    # it's a generator.

    return index if isinstance(index, six.string_types) else 'other'

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
    ('send_request', None),  # No target.
)

def wrap_elasticsearch_client_method(module, name, arg_extractor):
    def _nr_wrapper_ElasticSearch_method_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        # When arg_extractor is None, it means there is no target field
        # associated with this method. Hence this method will only create an
        # operation metric and no statement metric. This is handled by setting
        # the target to None when calling the DatastoreTrace.

        if arg_extractor is None:
            index = None
        else:
            index = arg_extractor(*args, **kwargs)

        with DatastoreTrace(transaction, product='Elasticsearch',
                target=index, operation=name):
            return wrapped(*args, **kwargs)

    if hasattr(module.ElasticSearch, name):
        wrap_function_wrapper(module.ElasticSearch, name,
                _nr_wrapper_ElasticSearch_method_)

def instrument_pyelasticsearch_client(module):
    for name, arg_extractor in _elasticsearch_client_methods:
        wrap_elasticsearch_client_method(module, name, arg_extractor)
