from newrelic.agent import wrap_function_trace
from newrelic.api.datastore_trace import wrap_datastore_trace

_methods = ['save', 'insert', 'update', 'drop', 'remove', 'find_one',
            'find', 'count', 'create_index', 'ensure_index', 'drop_indexes',
            'drop_index', 'reindex', 'index_information', 'options',
            'group', 'rename', 'distinct', 'map_reduce', 'inline_map_reduce',
            'find_and_modify']

def instrument_pymongo_connection(module):

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(module, 'Connection.__init__',
            name='%s:Connection.__init__' % module.__name__)

def instrument_pymongo_mongo_client(module):

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(module, 'MongoClient.__init__',
            name='%s:MongoClient.__init__' % module.__name__)

def instrument_pymongo_collection(module):

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    def _collection_name(collection, *args, **kwargs):
        return collection.name

    for method in _methods:
        if hasattr(module.Collection, method):
            wrap_datastore_trace(module, 'Collection.%s' % method,
                    product='MongoDB', target=_collection_name,
                    operation=method)
