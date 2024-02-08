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

import uuid

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version_tuple

# from newrelic.packages import six

PINECONE_VERSION = get_package_version_tuple("pinecone")


# Index extractor functions:


def bind_index_as_name(name, *args, **kwargs):
    return name


def bind_index_as_source(source, *args, **kwargs):
    return source


# List of Index and Pinecone methods:

Index_methods = (
    ("upsert", None),
    ("delete", None),
    ("fetch", None),
    ("query", None),
    ("update", None),
    ("describe_index_stats", None),
)

Pinecone_methods = (
    ("create_index", bind_index_as_name),
    ("delete_index", bind_index_as_name),
    ("describe_index", bind_index_as_name),
    ("list_indexes", None),
    ("create_collection", bind_index_as_source),
    ("describe_collection", None),
    ("list_collections", None),
    ("delete_collection", None),
    ("configure_index", None),
)


# Instrumentation:


def instrument_pinecone_methods(module, class_name, methods):
    for method_name, index_name in methods:
        if hasattr(getattr(module, class_name), method_name):
            wrap_pinecone_method(module, class_name, method_name, index_name)


def wrap_pinecone_method(module, class_name, method_name, index_name_function):
    def wrapper_pinecone_method(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        index = index_name_function and index_name_function(*args, **kwargs)

        # Obtain attributes to be stored on pinecone spans regardless of whether we hit an error
        pinecone_id = str(uuid.uuid4())

        # Get Pinecone API key without using the response so we can store it before the response is returned in case of errors
        # api_key = getattr(instance._client, "api_key", "") if OPENAI_V1 else getattr(openai, "api_key", None)
        # api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

        # Pinecone class has a self.config, which will have host info
        # Index class has a self._config, which will have host info
        if class_name == "Index":
            host = instance._config.host
        elif class_name == "Pinecone":
            host = instance.config.host
        else:
            host = None

        with DatastoreTrace(product="Pinecone", target=index, operation=method_name, host=host, source=wrapped) as dt:
            try:
                result = wrapped(*args, **kwargs)
                # store attributes to dt like pinecone_id, api_key_last_four_digits
                # dt.add_custom_attribute()
            except Exception as exc:
                # Error Logic goes here
                # error code, error message, error status code
                # look at OpenAI code for ideas
                # dt.notice_error(attributes=error_attributes)
                raise

            return result

    wrap_function_wrapper(module, "%s.%s" % (class_name, method_name), wrapper_pinecone_method)


def instrument_pinecone_data_index(module):
    instrument_pinecone_methods(module, "Index", Index_methods)


def instrument_pinecone_control_pinecone(module):
    instrument_pinecone_methods(module, "Pinecone", Pinecone_methods)


# For tests, first test all functions standalone, then have tests that run from OpenAI, Amazon Bedrock, and LangChain

# def wrap_Index_upsert(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="upsert", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# def wrap_Index_delete(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="delete", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# def wrap_Index_fetch(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="fetch", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# def wrap_Index_query(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="query", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# def wrap_Index_update(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="update", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# def wrap_Index_describe_index_stats(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Index class has a self._config, which will have host info
#     host = instance._config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="describe_index_stats", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)

#         return result


# # TODO: See about consolidating Pinecone class instrumenation
# # for methods as well.  This will be trickier than the one
# # for Index, but should be doable with some additional logic.
# # Use elasticsearch or redis as model

# def wrap_Pinecone_create_index(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     def bind_create_index(name, *args, **kwargs):
#         return name

#     index = bind_create_index(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=index, operation="create_index", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_delete_index(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     def bind_delete_index(name, *args, **kwargs):
#         return name

#     index = bind_delete_index(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=index, operation="delete_index", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_list_indexes(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="list_indexes", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_describe_index(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     def bind_describe_index(name, *args, **kwargs):
#         return name

#     index = bind_describe_index(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=index, operation="describe_index", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_configure_index(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     def bind_configure_index(name, *args, **kwargs):
#         return name

#     index = bind_configure_index(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=index, operation="configure_index", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_create_collection(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     def bind_create_collection(source, *args, **kwargs):
#         return source

#     index = bind_create_collection(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=index, operation="create_collection", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_list_collections(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="list_collections", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_delete_collection(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="delete_collection", host=host, source=wrapped):
#         return wrapped(*args, **kwargs)


# def wrap_Pinecone_describe_collection(wrapped, instance, args, kwargs):
#     transaction = current_transaction()

#     if transaction is None:
#         return wrapped(*args, **kwargs)

#     # Pinecone class has a self.config, which will have host info
#     host = instance.config.host

#     with DatastoreTrace(product="Pinecone", target=None, operation="describe_collection", host=host, source=wrapped):
#         result = wrapped(*args, **kwargs)


# def instrument_data_index(module):
#     if hasattr(module, "Index") and hasattr(module.Index, "upsert"):
#         wrap_function_wrapper(module, "Index.upsert", wrap_Index_upsert)
#     if hasattr(module, "Index") and hasattr(module.Index, "delete"):
#         wrap_function_wrapper(module, "Index.delete", wrap_Index_delete)
#     if hasattr(module, "Index") and hasattr(module.Index, "fetch"):
#         wrap_function_wrapper(module, "Index.fetch", wrap_Index_fetch)
#     if hasattr(module, "Index") and hasattr(module.Index, "query"):
#         wrap_function_wrapper(module, "Index.query", wrap_Index_query)
#     if hasattr(module, "Index") and hasattr(module.Index, "update"):
#         wrap_function_wrapper(module, "Index.update", wrap_Index_update)
#     if hasattr(module, "Index") and hasattr(module.Index, "describe_index_stats"):
#         wrap_function_wrapper(module, "Index.describe_index_stats", wrap_Index_describe_index_stats)


# def instrument_control_pinecone(module):
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "create_index"):
#         wrap_function_wrapper(module, "Pinecone.create_index", wrap_Pinecone_create_index)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "delete_index"):
#         wrap_function_wrapper(module, "Pinecone.delete_index", wrap_Pinecone_delete_index)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "list_indexes"):
#         wrap_function_wrapper(module, "Pinecone.list_indexes", wrap_Pinecone_list_indexes)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "describe_index"):
#         wrap_function_wrapper(module, "Pinecone.describe_index", wrap_Pinecone_describe_index)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "configure_index"):
#         wrap_function_wrapper(module, "Pinecone.configure_index", wrap_Pinecone_configure_index)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "create_collection"):
#         wrap_function_wrapper(module, "Pinecone.create_collection", wrap_Pinecone_create_collection)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "list_collections"):
#         wrap_function_wrapper(module, "Pinecone.list_collections", wrap_Pinecone_list_collections)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "delete_collection"):
#         wrap_function_wrapper(module, "Pinecone.delete_collection", wrap_Pinecone_delete_collection)
#     if hasattr(module, "Pinecone") and hasattr(module.Pinecone, "describe_collection"):
#         wrap_function_wrapper(module, "Pinecone.describe_collection", wrap_Pinecone_describe_collection)
