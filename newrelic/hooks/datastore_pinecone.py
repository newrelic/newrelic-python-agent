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

import json
import uuid

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version

PINECONE_VERSION = get_package_version("pinecone")


# Index extractor functions:


def bind_index_as_name(name, *args, **kwargs):
    return name


def bind_index_as_source(name, source, *args, **kwargs):
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
    ("configure_index", bind_index_as_name),
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
        transaction.add_ml_model_info("Pinecone", PINECONE_VERSION)

        # Obtain attributes to be stored on pinecone spans regardless of whether we hit an error
        pinecone_id = str(uuid.uuid4())
        # Framework from which Pinecone was called (if any)
        # index name (whatever is the current index)
        # collection name (if collection command used)

        # Get Pinecone API key without using the response so we can store
        # it before the response is returned in case of errors
        # Pinecone class has a self.config, which will have host info
        # Index class has a self._config, which will have host info
        if hasattr(instance, "config"):
            api_key = getattr(instance.config, "api_key", "")
            host = getattr(instance.config, "host", None)
        elif hasattr(instance, "_config"):
            api_key = getattr(instance._config, "api_key", "")
            host = getattr(instance._config, "host", None)
        else:
            api_key = None
            host = None

        api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

        attributes = {"id": pinecone_id, "api_key_last_four_digits": api_key_last_four_digits}

        with DatastoreTrace(product="Pinecone", target=index, operation=method_name, host=host, source=wrapped) as dt:
            try:
                result = wrapped(*args, **kwargs)
                dt.add_custom_attribute("id", pinecone_id)
                dt.add_custom_attribute("api_key_last_four_digits", api_key_last_four_digits)
            except Exception as exc:
                body = None
                if hasattr(exc, "body"):
                    try:
                        body = json.loads(exc.body)
                    except:
                        body = None

                code = getattr(exc, "reason", None) if not body else body.get("error", None).get("code", None)
                message = getattr(exc, "body", None) if not body else body.get("error", None).get("message", None)
                status = getattr(exc, "status", None)

                error_attributes = {
                    "http.statusCode": status,
                    "error.code": code,
                }.update(attributes)

                # Override the default message if it is not empty.
                if message:
                    exc._nr_message = message

                dt.notice_error(attributes=error_attributes)
                raise

            return result

    wrap_function_wrapper(module, "%s.%s" % (class_name, method_name), wrapper_pinecone_method)


def instrument_pinecone_data_index(module):
    instrument_pinecone_methods(module, "Index", Index_methods)


def instrument_pinecone_control_pinecone(module):
    instrument_pinecone_methods(module, "Pinecone", Pinecone_methods)
