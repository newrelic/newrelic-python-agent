import sys
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import (
        function_wrapper, wrap_function_wrapper)
from newrelic.common.object_names import callable_name


_VERSION = None


def _store_version_info():
    import tornado
    global _VERSION

    try:
        _VERSION = '.'.join(map(str, tornado.version_info))
    except:
        pass

    return tornado.version_info


def _bind_start_request(server_conn, request_conn, *args, **kwargs):
    return request_conn


def _bind_headers_received(start_line, headers, *args, **kwargs):
    return start_line, headers


def wrap_headers_received(request_conn, headers_received):

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

        # Restore the original headers_received method in order to prevent side
        # effects from the message delegate holding a reference to the
        # connection
        instance.headers_received = headers_received

        return wrapped(*args, **kwargs)

    return _wrap_headers_received


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
    headers_received = message_delegate.headers_received
    wrapper = wrap_headers_received(request_conn, headers_received)
    message_delegate.headers_received = wrapper(headers_received)

    # Wrap finish (response has been written)
    finish = request_conn.finish
    request_conn.finish = wrap_finish(finish)

    return message_delegate


def instrument_tornado_httpserver(module):
    version_info = _store_version_info()

    # Do not instrument Tornado versions < 6.0
    if version_info[0] < 6:
        return

    wrap_function_wrapper(
            module, 'HTTPServer.start_request', wrap_start_request)
