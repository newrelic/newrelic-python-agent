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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.datastore_trace import wrap_datastore_trace
from newrelic.api.function_trace import wrap_function_trace
from newrelic.common.async_wrapper import generator_wrapper
from newrelic.api.datastore_trace import DatastoreTrace

_firestore_document_commands = (
    "create",
    "delete",
    "get",
    "set",
    "update",
)
_firestore_document_generator_commands = (
    "collections",
)

_firestore_collection_commands = (
    "add",
    "get",
)
_firestore_collection_generator_commands = (
    "stream",
    "list_documents"
)

_get_object_id = lambda obj, *args, **kwargs: obj.id


def wrap_generator_method(module, class_name, method_name):
    def _wrapper(wrapped, instance, args, kwargs):
        trace = DatastoreTrace(product="Firestore", target=instance.id, operation=method_name)
        wrapped = generator_wrapper(wrapped, trace)
        return wrapped(*args, **kwargs)
    
    class_ = getattr(module, class_name)
    if class_ is not None:
        if hasattr(class_, method_name):
            wrap_function_wrapper(module, "%s.%s" % (class_name, method_name), _wrapper)


def instrument_google_cloud_firestore_v1_base_client(module):
    rollup = ("Datastore/all", "Datastore/Firestore/all")
    wrap_function_trace(
        module, "BaseClient.__init__", name="%s:BaseClient.__init__" % module.__name__, terminal=True, rollup=rollup
    )


def instrument_google_cloud_firestore_v1_base_collection(module):
    for name in _firestore_collection_commands:
        if hasattr(module.BaseCollectionReference, name) and not getattr(getattr(module.BaseCollectionReference, name), "_nr_wrapped", False):
            wrap_datastore_trace(
                module, "BaseCollectionReference.%s" % name, product="Firestore", target=_get_object_id, operation=name
            )
            getattr(module.BaseCollectionReference, name)._nr_wrapped = True

    for name in _firestore_collection_generator_commands:
        if hasattr(module.BaseCollectionReference, name) and not getattr(getattr(module.BaseCollectionReference, name), "_nr_wrapped", False):
            wrap_generator_method(module, "BaseCollectionReference", name)
            getattr(module.BaseCollectionReference, name)._nr_wrapped = True


def instrument_google_cloud_firestore_v1_collection(module):
    for name in _firestore_collection_commands:
        if hasattr(module.CollectionReference, name) and not getattr(getattr(module.CollectionReference, name), "_nr_wrapped", False):
            wrap_datastore_trace(
                module, "CollectionReference.%s" % name, product="Firestore", target=_get_object_id, operation=name
            )
            getattr(module.CollectionReference, name)._nr_wrapped = True

    for name in _firestore_collection_generator_commands:
        if hasattr(module.CollectionReference, name) and not getattr(getattr(module.CollectionReference, name), "_nr_wrapped", False):
            wrap_generator_method(module, "CollectionReference", name)
            getattr(module.CollectionReference, name)._nr_wrapped = True


def instrument_google_cloud_firestore_v1_base_document(module):
    for name in _firestore_document_commands:
        if hasattr(module.BaseDocumentReference, name) and not getattr(getattr(module.BaseDocumentReference, name), "_nr_wrapped", False):
            wrap_datastore_trace(
                module, "BaseDocumentReference.%s" % name, product="Firestore", target=_get_object_id, operation=name
            )
            getattr(module.BaseDocumentReference, name)._nr_wrapped = True

    for name in _firestore_document_generator_commands:
        if hasattr(module.BaseDocumentReference, name) and not getattr(getattr(module.BaseDocumentReference, name), "_nr_wrapped", False):
            wrap_generator_method(module, "BaseDocumentReference", name)
            getattr(module.BaseDocumentReference, name)._nr_wrapped = True


def instrument_google_cloud_firestore_v1_document(module):
    for name in _firestore_document_commands:
        if hasattr(module.DocumentReference, name) and not getattr(getattr(module.DocumentReference, name), "_nr_wrapped", False):
            wrap_datastore_trace(
                module, "DocumentReference.%s" % name, product="Firestore", target=_get_object_id, operation=name
            )
            getattr(module.DocumentReference, name)._nr_wrapped = True

    for name in _firestore_document_generator_commands:
        if hasattr(module.DocumentReference, name) and not getattr(getattr(module.DocumentReference, name), "_nr_wrapped", False):
            wrap_generator_method(module, "DocumentReference", name)
            getattr(module.DocumentReference, name)._nr_wrapped = True
