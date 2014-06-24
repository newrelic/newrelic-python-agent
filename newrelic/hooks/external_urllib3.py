from newrelic.agent import (current_transaction,
        wrap_function_wrapper, ExternalTrace)

def _nr_wrapper_make_request_(wrapped, instance, args, kwargs):

    def _bind_params(conn, method, url, *args, **kwargs):
        return "http://%s" % conn.host

    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    url_for_apm_ui = _bind_params(*args, **kwargs)

    with ExternalTrace(transaction, 'urllib3', url_for_apm_ui):
        return wrapped(*args, **kwargs)

def instrument(module):

    if hasattr(module, 'HTTPConnectionPool'):
        wrap_function_wrapper(module, 'HTTPConnectionPool._make_request',
                _nr_wrapper_make_request_)

