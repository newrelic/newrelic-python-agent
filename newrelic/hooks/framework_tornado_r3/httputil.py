import logging
import traceback
import weakref

from newrelic.agent import (application as application_instance, callable_name,
        WebTransaction, wrap_function_wrapper)
from .util import purge_current_transaction

_logger = logging.getLogger(__name__)

# We need a request to start monitoring a transaction (or we need to compute
# some values that will be recomputed when the request gets created) so we
# initiate our instrumentation here.
# We may need to handle wsgi apps differently.

def _nr_wrapper_HTTPServerRequest__init__(wrapped, instance, args, kwargs):
    # This is the first point of entry into our instrumentation. It gets called
    # after header but before the request body is read in one of 3 possible
    # places:
    #   web.py: The normal case when the application passed to the HTTPServer
    #     is an Tornado 4 Application object.
    #   httpserver.py: A strange case where the application passed to the
    #     HTTPServer is not a Tornado 4 Application object (so the
    #     HTTPServerAdapter has no delegate).
    #   wsgi.py: Needs more exploration.
    #
    # After this is called the request body may be streamed or not depending on
    # the application configuration (see tornado.web.stream_request_body).

    assert instance is not None

    result = wrapped(*args, **kwargs)

    # instance is now an initiated HTTPServerRequest object. Since instance was
    # just created there can not be a previously associated transaction.

    request = instance

    if is_websocket(request):
        transaction = None
    else:
        transaction = initiate_request_monitoring(request)

    # Transaction can still be None at this point, if it wasn't enabled during
    # WebTransaction.__init__().

    if transaction:

        # Name transaction initially after the wrapped function so that if
        # the connection is dropped before all the request content is read,
        # then we don't get metric grouping issues with it being named after
        # the URL.

        name = callable_name(wrapped)
        transaction.set_transaction_name(name)

        # Use HTTPServerRequest start time as transaction start time.

        transaction.start_time = request._start_time

    # Even if transaction is `None`, we still attach it to the request, so we
    # can distinguish between a missing _nr_transaction attribute (error) from
    # the case where _nr_transaction is None (ok).

    request._nr_transaction = transaction

    return result

def initiate_request_monitoring(request):
    # Creates a new transaction and associates it with the request.
    # We always use the default application specified in the agent
    # configuration.

    application = application_instance()

    # We need to fake up a WSGI like environ dictionary with the key
    # bits of information we need.

    environ = request_environment(application, request)

    # We now start recording the actual web transaction.

    purge_current_transaction()

    transaction = WebTransaction(application, environ)
    transaction.__enter__()

    # Immediately purge the transaction from the cache, so we don't associate
    # Tornado internals inappropriately with this transaction.

    purge_current_transaction()

    # We also need to add a reference to the request object in to the
    # transaction object so we can later access it in a deferred. We
    # need to use a weakref to avoid an object cycle which may prevent
    # cleanup of the transaction.

    transaction._nr_current_request = weakref.ref(request)

    # Records state of transaction

    transaction._is_finalized = False
    transaction._ref_count = 0

    # For server requests We only allow the transaction to be closed when
    # either 'finish' or 'on_connection_close' is called on an
    # associated HTTPMessageDelegate.

    transaction._can_finalize = False

    # Record framework information for generation of framework metrics.

    import tornado

    if hasattr(tornado, 'version_info'):
        version = '.'.join(map(str, tornado.version_info))
    else:
        version = None

    transaction.add_framework_info('Tornado/ASYNC', version)

    return transaction

def request_environment(application, request):
    # This creates a WSGI environ dictionary from a Tornado request.

    result = getattr(request, '_nr_request_environ', None)

    if result is not None:
        return result

    # We don't bother if the agent hasn't as yet been registered.

    settings = application.settings

    if not settings:
        return {}

    request._nr_request_environ = result = {}

    result['REQUEST_URI'] = request.uri
    result['QUERY_STRING'] = request.query

    value = request.headers.get('X-NewRelic-ID')
    if value:
        result['HTTP_X_NEWRELIC_ID'] = value

    value = request.headers.get('X-NewRelic-Transaction')
    if value:
        result['HTTP_X_NEWRELIC_TRANSACTION'] = value

    value = request.headers.get('X-Request-Start')
    if value:
        result['HTTP_X_REQUEST_START'] = value

    value = request.headers.get('X-Queue-Start')
    if value:
        result['HTTP_X_QUEUE_START'] = value

    for key in settings.include_environ:
        if key == 'REQUEST_METHOD':
            result[key] = request.method
        elif key == 'HTTP_USER_AGENT':
            value = request.headers.get('User-Agent')
            if value:
                result[key] = value
        elif key == 'HTTP_REFERER':
            value = request.headers.get('Referer')
            if value:
                result[key] = value
        elif key == 'CONTENT_TYPE':
            value = request.headers.get('Content-Type')
            if value:
                result[key] = value
        elif key == 'CONTENT_LENGTH':
            value = request.headers.get('Content-Length')
            if value:
                result[key] = value

    return result

def is_websocket(request):
    return request.headers.get('Upgrade', '').lower() == 'websocket'

def instrument_tornado_httputil(module):
    wrap_function_wrapper(module, 'HTTPServerRequest.__init__',
            _nr_wrapper_HTTPServerRequest__init__)
