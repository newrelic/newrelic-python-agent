from newrelic.agent import function_wrapper, wrap_function_wrapper

from .util import retrieve_current_transaction, possibly_finalize_transaction


def _nr_wrapper_curl_httpclient_CurlAsyncHTTPClient_fetch_impl_(wrapped,
        instance, args, kwargs):

    def _bind_params(request, callback, *args, **kwargs):
        return request, callback

    _, callback = _bind_params(*args, **kwargs)

    if callback:
        transaction = retrieve_current_transaction()

        if transaction:
            transaction._ref_count += 1

            @function_wrapper
            def _nr_wrapper_decrementer(_wrapped, _instance, _args, _kwargs):
                try:
                    return _wrapped(*_args, **_kwargs)
                finally:
                    transaction._ref_count -= 1
                    possibly_finalize_transaction(transaction)

            wrapped_callback = _nr_wrapper_decrementer(callback)

            # Replace callback with one that will decrement the ref_count
            # when it runs.

            if len(args) > 0:
                args = list(args)
                args[1] = wrapped_callback
            else:
                kwargs['callback'] = wrapped_callback

    return wrapped(*args, **kwargs)


def instrument_tornado_curl_httpclient(module):
    wrap_function_wrapper(module, 'CurlAsyncHTTPClient.fetch_impl',
            _nr_wrapper_curl_httpclient_CurlAsyncHTTPClient_fetch_impl_)
