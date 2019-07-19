import inspect
import sys
from newrelic.api.function_trace import function_trace
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import current_trace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import (
        function_wrapper, wrap_function_wrapper)
from newrelic.common.object_names import callable_name


_VERSION = None
_instrumented = set()


def _store_version_info():
    import tornado
    global _VERSION

    try:
        _VERSION = '.'.join(map(str, tornado.version_info))
    except:
        pass

    return tornado.version_info


def _wrap_if_not_wrapped(obj, attr, wrapper):
    wrapped = getattr(obj, attr, None)

    if not callable(wrapped):
        return

    if not (hasattr(wrapped, '__wrapped__') and
            wrapped.__wrapped__ in _instrumented):
        setattr(obj, attr, wrapper(wrapped))
        _instrumented.add(wrapped)


def _bind_start_request(server_conn, request_conn, *args, **kwargs):
    return request_conn


def _bind_headers_received(start_line, headers, *args, **kwargs):
    return start_line, headers


def wrap_headers_received(request_conn):

    @function_wrapper
    def _wrap_headers_received(wrapped, instance, args, kwargs):
        start_line, headers = _bind_headers_received(*args, **kwargs)
        port = None

        try:
            # We only want to record port for ipv4 and ipv6 socket families.
            # Unix socket will just return a string instead of a tuple, so
            # skip this.
            sockname = request_conn.stream.socket.getsockname()
            if isinstance(sockname, tuple):
                port = sockname[1]
        except:
            pass

        path, sep, query = start_line.path.partition('?')

        transaction = WebTransaction(
            application=application_instance(),
            name=callable_name(instance),
            port=port,
            request_method=start_line.method,
            request_path=path,
            query_string=query,
            headers=headers,
        )
        transaction.__enter__()

        if not transaction.enabled:
            return wrapped(*args, **kwargs)

        transaction.add_framework_info('Tornado', _VERSION)

        # Store the transaction on the HTTPMessageDelegate object since the
        # transaction lives for the lifetime of that object.
        request_conn._nr_transaction = transaction

        # Remove the headers_received circular reference
        vars(instance).pop('headers_received')

        return wrapped(*args, **kwargs)

    return _wrap_headers_received


def _bind_response_headers(start_line, headers, *args, **kwargs):
    return start_line.code, headers


@function_wrapper
def wrap_write_headers(wrapped, instance, args, kwargs):
    transaction = getattr(instance, '_nr_transaction', None)

    if transaction:
        http_status, headers = _bind_response_headers(*args, **kwargs)
        cat_headers = transaction.process_response(http_status, headers)

        for name, value in cat_headers:
            headers.add(name, value)

    return wrapped(*args, **kwargs)


@function_wrapper
def wrap_finish(wrapped, instance, args, kwargs):
    try:
        return wrapped(*args, **kwargs)
    finally:
        transaction = getattr(instance, '_nr_transaction', None)
        if transaction:
            transaction.__exit__(*sys.exc_info())
            instance._nr_transaction = None


def wrap_start_request(wrapped, instance, args, kwargs):
    request_conn = _bind_start_request(*args, **kwargs)
    message_delegate = wrapped(*args, **kwargs)

    # Wrap headers_received (request method / path is known)
    wrapper = wrap_headers_received(request_conn)
    message_delegate.headers_received = wrapper(
            message_delegate.headers_received)

    # Wrap write_headers to get response
    _wrap_if_not_wrapped(
            type(request_conn), 'write_headers', wrap_write_headers)

    # Wrap finish (response has been written)
    _wrap_if_not_wrapped(
            type(request_conn), 'finish', wrap_finish)

    return message_delegate


def instrument_tornado_httpserver(module):
    version_info = _store_version_info()

    # Do not instrument Tornado versions < 6.0
    if version_info[0] < 6:
        return

    wrap_function_wrapper(
            module, 'HTTPServer.start_request', wrap_start_request)


def _nr_wrapper__NormalizedHeaderCache___missing__(
        wrapped, instance, args, kwargs):

    def _bind_params(key, *args, **kwargs):
        return key

    key = _bind_params(*args, **kwargs)

    normalized = wrapped(*args, **kwargs)

    if key.startswith('X-NewRelic'):
        instance[key] = key
        return key

    return normalized


def instrument_tornado_httputil(module):
    wrap_function_wrapper(module, '_NormalizedHeaderCache.__missing__',
            _nr_wrapper__NormalizedHeaderCache___missing__)


def _extract_request(request, raise_error=True, **_kwargs):
    return request, None, raise_error, _kwargs


def _prepare_request(*args, **kwargs):
    from tornado.httpclient import HTTPRequest

    request, callback, raise_error, _kwargs = _extract_request(*args,
            **kwargs)

    # request is either a string or a HTTPRequest object
    if not isinstance(request, HTTPRequest):
        url = request
        request = HTTPRequest(url, **_kwargs)

    callback_kwargs = {}
    if callback:
        callback_kwargs['callback'] = callback

    return request, raise_error, callback_kwargs


def wrap_handle_response(raise_error, trace):
    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        def _bind_params(response, *args, **kwargs):
            return response

        response = _bind_params(*args, **kwargs)

        # Process CAT response headers
        trace.process_response_headers(response.headers.get_all())

        trace.__exit__(None, None, None)

        return result
    return wrapper


@function_wrapper
def wrap_fetch_impl(wrapped, instance, args, kwargs):
    _nr_args = getattr(instance, '_nr_args', None)

    if not _nr_args:
        return wrapped(*args, **kwargs)

    def _bind_params(request, callback, *args, **kwargs):
        return request, callback

    request, handle_response = _bind_params(*args, **kwargs)
    wrapped_handle_response = wrap_handle_response(*_nr_args)(handle_response)

    return wrapped(request, wrapped_handle_response)


def _nr_wrapper_httpclient_AsyncHTTPClient_fetch_(
        wrapped, instance, args, kwargs):

    parent_trace = current_trace()

    if parent_trace is None:
        return wrapped(*args, **kwargs)
    transaction = parent_trace.transaction

    try:
        req, _raise_error, _kwargs = _prepare_request(*args, **kwargs)
    except:
        return wrapped(*args, **kwargs)

    # Prepare outgoing CAT headers
    outgoing_headers = ExternalTrace.generate_request_headers(transaction)
    for header_name, header_value in outgoing_headers:
        # User headers should override our CAT headers
        if header_name in req.headers:
            continue
        req.headers[header_name] = header_value

    # wrap the fetch_impl on the unbound method
    instance_type = type(instance)
    if not hasattr(instance_type, '_nr_wrapped'):
        instance_type.fetch_impl = wrap_fetch_impl(instance_type.fetch_impl)
        instance_type._nr_wrapped = True

    trace = ExternalTrace('tornado.httpclient', req.url, req.method.upper(),
        parent=parent_trace)
    instance._nr_args = (_raise_error, trace)

    with trace:
        return wrapped(req, raise_error=_raise_error, **_kwargs)


def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'AsyncHTTPClient.fetch',
            _nr_wrapper_httpclient_AsyncHTTPClient_fetch_)


def _nr_rulerouter_process_rule(wrapped, instance, args, kwargs):
    def _bind_params(rule, *args, **kwargs):
        return rule

    rule = _bind_params(*args, **kwargs)

    _wrap_handlers(rule)

    return wrapped(*args, **kwargs)


@function_wrapper
def _nr_method(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    if getattr(transaction, '_method_seen', None):
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)
    transaction.set_transaction_name(name, priority=2)
    transaction._method_seen = True
    return function_trace(name=name)(wrapped)(*args, **kwargs)


def _wrap_handlers(rule):
    if isinstance(rule, (tuple, list)):
        handler = rule[1]
    elif hasattr(rule, 'target'):
        handler = rule.target
    elif hasattr(rule, 'handler_class'):
        handler = rule.handler_class
    else:
        return

    from tornado.web import RequestHandler
    from tornado.websocket import WebSocketHandler

    if isinstance(handler, (tuple, list)):
        # Tornado supports nested rules. For example
        #
        # application = web.Application([
        #     (HostMatches("example.com"), [
        #         (r"/", MainPageHandler),
        #         (r"/feed", FeedHandler),
        #     ]),
        # ])
        for subrule in handler:
            _wrap_handlers(subrule)
        return

    elif (not inspect.isclass(handler) or
            issubclass(handler, WebSocketHandler) or
            not issubclass(handler, RequestHandler)):
        # This handler does not inherit from RequestHandler so we ignore it.
        # Tornado supports non class based views and this is probably one of
        # those. It has also been observed that tornado's internals will pass
        # class instances as well.
        return

    if not hasattr(handler, 'SUPPORTED_METHODS'):
        return

    # Wrap all supported view methods with our FunctionTrace
    # instrumentation
    for request_method in handler.SUPPORTED_METHODS:
        _wrap_if_not_wrapped(handler, request_method.lower(), _nr_method)


def _nr_wrapper_web_errorhandler_init(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(instance)
    transaction.set_transaction_name(name, priority=2)
    return wrapped(*args, **kwargs)


def _nr_wrapper_web_requesthandler_init(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(instance)
    transaction.set_transaction_name(name, priority=1)
    return wrapped(*args, **kwargs)


def instrument_tornado_routing(module):
    wrap_function_wrapper(module, 'RuleRouter.process_rule',
            _nr_rulerouter_process_rule)


def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'ErrorHandler.__init__',
            _nr_wrapper_web_errorhandler_init)

    wrap_function_wrapper(module, 'RequestHandler.__init__',
            _nr_wrapper_web_requesthandler_init)
