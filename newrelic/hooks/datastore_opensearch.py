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

import inspect

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import snake_case
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.config import global_settings

# Public attributes present on the client classes that are not OpenSearch API
# operations and must never be wrapped.
_IGNORED_METHODS = frozenset({"perform_request", "transport", "options"})


def _index_name(index):
    # An index name can be a string, None or a sequence. In the case of None,
    # an empty string or '*', it is the same as using '_all'. When a string
    # it can also be a comma separated list of index names. A sequence
    # obviously can also be more than one index name. Where we are certain
    # there is only a single index name we use it, otherwise we use 'other'.
    if not index or index == "*":
        return "_all"
    if not isinstance(index, str) or "," in index:
        return "other"
    return index


def _namespace_prefix(class_name):
    # Convert a namespace client class name into the operation prefix.
    # eg. DanglingIndicesClient -> dangling_indices
    return snake_case(class_name.removesuffix("Client"))


def _make_index_arg_extractor(method):
    # Build a callable that pulls the index argument out of a client
    # method's call args, or return None when the method has no index
    # parameter (making it an operation-only metric with no target).

    # The method's signature is inspected once at import time so the
    # runtime cost is kept low. OpenSearch 3.x makes these methods
    # keyword-only, but the positional fallback keeps older
    # positional-style releases working.

    try:
        params = list(inspect.signature(method).parameters)
    except (TypeError, ValueError):
        return None

    if "index" not in params:
        # If index is not in the param list, we don't return an extractor
        # which signals to the instrumentation the target should be None.
        return None

    # params includes the leading self reference. The object wrapper passes
    # call args without the bound instance, so the positional offset is one less.
    position = params.index("index") - 1

    def _extract_index(*args, **kwargs):
        # A method that accepts an index argument but is called without one is
        # targeting every index, which _index_name(None) reports as "_all".
        # This is distinct from a method that has no index argument at all,
        # which is handled above and will report as None.
        if "index" in kwargs:
            index = kwargs["index"]
        elif 0 <= position < len(args):
            index = args[position]
        else:
            index = None
        return _index_name(index)

    return _extract_index


def wrap_opensearch_client_method(module, class_name, method_name, arg_extractor, prefix=None):
    def _wrap_opensearch_client_method(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        # A target (index) is only recorded for methods that accept one; the
        # rest produce an operation-only metric with target=None.
        index = arg_extractor(*args, **kwargs) if arg_extractor is not None else None
        operation = f"{prefix}.{method_name}" if prefix else method_name

        # Host/port instance info is filled in during the call by the transport's
        # get_connection wrapper below, not from the response.
        with DatastoreTrace(product="OpenSearch", target=index, operation=operation, source=wrapped):
            return wrapped(*args, **kwargs)

    wrap_function_wrapper(module, f"{class_name}.{method_name}", _wrap_opensearch_client_method)


def wrap_async_opensearch_client_method(module, class_name, method_name, arg_extractor, prefix=None):
    async def _wrap_async_opensearch_client_method(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return await wrapped(*args, **kwargs)

        index = arg_extractor(*args, **kwargs) if arg_extractor is not None else None
        operation = f"{prefix}.{method_name}" if prefix else method_name

        with DatastoreTrace(product="OpenSearch", target=index, operation=operation, source=wrapped):
            return await wrapped(*args, **kwargs)

    wrap_function_wrapper(module, f"{class_name}.{method_name}", _wrap_async_opensearch_client_method)


def wrap_Connection__init__(wrapped, instance, args, kwargs):
    # Cache datastore instance info on the Connection object.
    result = wrapped(*args, **kwargs)
    try:
        instance._nr_host_port = (instance.hostname, str(instance.port))
    except Exception:
        pass
    return result


def wrap_get_connection(wrapped, instance, args, kwargs):
    # Read instance info off the selected Connection and set it on the trace.

    # AsyncTransport.get_connection is a synchronous method, so the same wrapper
    # applies to both the sync and async transports.

    trace = current_trace()

    if trace is None or not isinstance(trace, DatastoreTrace):
        return wrapped(*args, **kwargs)

    conn = wrapped(*args, **kwargs)

    try:
        settings = trace.settings or global_settings()
        if settings.datastore_tracer.instance_reporting.enabled:
            trace.host, trace.port_path_or_id = conn._nr_host_port
    except Exception:
        trace.host, trace.port_path_or_id = "unknown", "unknown"

    return conn


def _instrument_client_class(module, client_class, wrapper, prefix=None):
    # Wrap every public API method on a client class using automatic discovery.
    for method_name in dir(client_class):
        if method_name.startswith("_") or method_name in _IGNORED_METHODS:
            continue  # If the attribute is private or ignored, skip it
        method = getattr(client_class, method_name, None)
        if not callable(method):
            continue  # If the attribute is not actually a callable method, skip it

        # Make an argument extractor and instrument the method
        arg_extractor = _make_index_arg_extractor(method)
        wrapper(module, client_class.__name__, method_name, arg_extractor, prefix)


def _instrument_all_clients(module, root_class_name, wrapper):
    # Instrument the root client plus every namespaced sub-client
    # exported on the module. NamespacedClient subclasses are
    # discovered automatically.
    from opensearchpy.client.utils import NamespacedClient

    # Instrument the root class
    root_class = getattr(module, root_class_name, None)
    if root_class is not None:
        _instrument_client_class(module, root_class, wrapper)

    # Instrument all NamespacedClient subclasses
    for name in dir(module):
        obj = getattr(module, name, None)
        if inspect.isclass(obj) and issubclass(obj, NamespacedClient) and obj is not NamespacedClient:
            _instrument_client_class(module, obj, wrapper, prefix=_namespace_prefix(obj.__name__))


def instrument_opensearch_client(module):
    _instrument_all_clients(module, "OpenSearch", wrap_opensearch_client_method)


def instrument_async_opensearch_client(module):
    _instrument_all_clients(module, "AsyncOpenSearch", wrap_async_opensearch_client_method)


def instrument_opensearch_connection_base(module):
    if hasattr(module, "Connection"):
        wrap_function_wrapper(module, "Connection.__init__", wrap_Connection__init__)


def instrument_opensearch_transport(module):
    if hasattr(module, "Transport") and hasattr(module.Transport, "get_connection"):
        wrap_function_wrapper(module, "Transport.get_connection", wrap_get_connection)


def instrument_async_opensearch_transport(module):
    if hasattr(module, "AsyncTransport") and hasattr(module.AsyncTransport, "get_connection"):
        wrap_function_wrapper(module, "AsyncTransport.get_connection", wrap_get_connection)
