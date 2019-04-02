import time

from newrelic.api.external_trace import ExternalTrace, wrap_external_trace
from newrelic.api.web_transaction import WebTransactionWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.object_names import callable_name


def _get_uri(instance, *args, **kwargs):
    target = instance._channel.target().decode('utf-8')
    method = instance._method.decode('utf-8').lstrip('/')
    return 'grpc://%s/%s' % (target, method)


def wrap_external_future(module, object_path, library, url, method=None):
    def _wrap_future(wrapped, instance, args, kwargs):
        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        future = wrapped(*args, **kwargs)
        future._nr_args = (transaction, library, _url, method)
        future._nr_result_called = False
        future._nr_start_time = time.time()

        # In non-streaming responses, result is typically called instead of
        # using the iterator. In streaming calls, the iterator is typically
        # used.

        return future

    wrap_function_wrapper(module, object_path, _wrap_future)


def wrap_next(_wrapped, _instance, _args, _kwargs):
    _nr_args = getattr(_instance, '_nr_args', None)
    if not _nr_args:
        return _wrapped(*_args, **_kwargs)

    _start = time.time()
    try:
        result = _wrapped(*_args, **_kwargs)
    except StopIteration:
        raise
    except Exception:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _start
            raise
    else:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _start
            return result


def wrap_result(_wrapped, _instance, _args, _kwargs):
    _result_called = getattr(_instance, '_nr_result_called', True)
    if _result_called:
        return _wrapped(*_args, **_kwargs)
    _instance._nr_result_called = True

    _nr_args = getattr(_instance, '_nr_args', None)
    if not _nr_args:
        return _wrapped(*_args, **_kwargs)

    _nr_start_time = getattr(_instance, '_nr_start_time', 0.0)

    try:
        result = _wrapped(*_args, **_kwargs)
    except Exception:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _nr_start_time
            raise
    else:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _nr_start_time
            return result


def _bind_transaction_args(rpc_event, state, behavior, *args, **kwargs):
    return rpc_event, behavior


def grpc_web_transaction(wrapped, instance, args, kwargs):
    rpc_event, behavior = _bind_transaction_args(*args, **kwargs)
    behavior_name = callable_name(behavior)

    call_details = (
            getattr(rpc_event, 'call_details', None) or
            getattr(rpc_event, 'request_call_details', None))

    metadata = (
            getattr(rpc_event, 'invocation_metadata', None) or
            getattr(rpc_event, 'request_metadata', None))

    host = port = None
    if call_details:
        try:
            host, port = call_details.host.split(b':', 1)
        except Exception:
            pass

        request_path = call_details.method

    return WebTransactionWrapper(
            wrapped,
            name=behavior_name,
            request_path=request_path,
            host=host,
            port=port,
            headers=metadata)(*args, **kwargs)


def _nr_wrap_status_code(wrapped, instance, args, kwargs):
    def _trailing_metadata(state, *args, **kwargs):
        return state.trailing_metadata

    status_code = wrapped(*args, **kwargs)
    response_headers = _trailing_metadata(*args, **kwargs)

    transaction = current_transaction()
    if transaction:
        transaction.process_response(status_code, response_headers)

    return status_code


def instrument_grpc__channel(module):
    wrap_external_trace(module, '_UnaryUnaryMultiCallable.__call__',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_trace(module, '_UnaryUnaryMultiCallable.with_call',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_future(module, '_UnaryUnaryMultiCallable.future',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_future(module, '_UnaryStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'unary_stream')
    wrap_external_trace(module, '_StreamUnaryMultiCallable.__call__',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_trace(module, '_StreamUnaryMultiCallable.with_call',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_future(module, '_StreamUnaryMultiCallable.future',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_future(module, '_StreamStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'stream_stream')
    wrap_function_wrapper(module, '_Rendezvous._next',
            wrap_next)
    wrap_function_wrapper(module, '_Rendezvous.result',
            wrap_result)


def instrument_grpc_server(module):
    wrap_function_wrapper(module, '_unary_response_in_pool',
            grpc_web_transaction)
    wrap_function_wrapper(module, '_stream_response_in_pool',
            grpc_web_transaction)
    wrap_function_wrapper(module, '_completion_code',
            _nr_wrap_status_code)
