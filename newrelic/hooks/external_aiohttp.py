import sys

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper, ObjectProxy


class NRRequestCoroutineWrapper(ObjectProxy):
    def __init__(self, url, method, wrapped, func=None):
        super(NRRequestCoroutineWrapper, self).__init__(wrapped)
        transaction = current_transaction()
        self._nr_trace = ExternalTrace(transaction,
                'aiohttp', url, method)

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        return self.send(None)

    def send(self, value):
        if not self._nr_trace.transaction:
            return self.__wrapped__.send(value)

        if not self._nr_trace.activated:
            self._nr_trace.__enter__()
            if self._nr_trace.transaction.current_node is self._nr_trace:
                # externals should not have children
                self._nr_trace.transaction._pop_current(self._nr_trace)

        try:
            return self.__wrapped__.send(value)
        except StopIteration as e:
            try:
                result = e.value
                self._nr_trace.process_response_headers(result.headers.items())
            except:
                pass

            self._nr_trace.__exit__(None, None, None)
            raise
        except Exception as e:
            try:
                self._nr_trace.process_response_headers(e.headers.items())
            except:
                pass

            self._nr_trace.__exit__(*sys.exc_info())
            raise

    def throw(self, *args, **kwargs):
        try:
            return self.__wrapped__.throw(*args, **kwargs)
        except:
            self._nr_trace.__exit__(*sys.exc_info())
            raise

    def close(self):
        try:
            r = self.__wrapped__.close()
            self._nr_trace.__exit__(None, None, None)
            return r
        except:
            self._nr_trace.__exit__(*sys.exc_info())
            raise


def _bind_request(method, url, *args, **kwargs):
    return method, url


def _nr_aiohttp_request_wrapper_(wrapped, instance, args, kwargs):
    coro = wrapped(*args, **kwargs)
    method, url = _bind_request(*args, **kwargs)
    return NRRequestCoroutineWrapper(url, method, coro, None)


def _bind_write_headers(status_line, headers, *args, **kwargs):
    return status_line, headers, args, kwargs


def _nr_wrap_PayloadWriter_write_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    status_line, headers, _args, _kwargs = _bind_write_headers(
            *args, **kwargs)

    try:
        cat_headers = ExternalTrace.generate_request_headers(transaction)
        updated_headers = dict(cat_headers + [(k, v) for k, v in
                headers.items()])
    except:
        return wrapped(*args, **kwargs)

    return wrapped(status_line, updated_headers, *_args, **_kwargs)


def instrument_aiohttp_client(module):
    wrap_function_wrapper(module, 'ClientSession._request',
            _nr_aiohttp_request_wrapper_)


def instrument_aiohttp_http_writer(module):
    wrap_function_wrapper(module, 'PayloadWriter.write_headers',
            _nr_wrap_PayloadWriter_write_headers)
