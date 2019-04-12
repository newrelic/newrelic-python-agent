import random
import time

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.web_transaction import WebTransactionWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.object_names import callable_name


def _get_uri(instance, *args, **kwargs):
    target = instance._channel.target().decode('utf-8')
    method = instance._method.decode('utf-8').lstrip('/')
    return 'grpc://%s/%s' % (target, method)


def _prepare_request(
        transaction, guid, request,
        timeout=None, metadata=None, *args, **kwargs):
    metadata = metadata and list(metadata) or []
    if transaction.settings.distributed_tracing.enabled:
        payload = transaction._create_distributed_trace_payload_with_guid(guid)
        if payload:
            headers = [
                (ExternalTrace.cat_distributed_trace_key, payload.http_safe()),
            ]
            headers.extend(metadata)
            metadata = headers

    kwargs['metadata'] = metadata
    return request, timeout, args, kwargs


def _prepare_request_stream(
        transaction, guid, request_iterator, *args, **kwargs):
    return _prepare_request(
            transaction, guid, request_iterator, *args, **kwargs)


def wrap_call(module, object_path, prepare, method):

    def _call_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        uri = _get_uri(instance)
        with ExternalTrace(transaction, 'gRPC', uri, method):
            request, timeout, args, kwargs = prepare(
                    transaction, None, *args, **kwargs)
            return wrapped(request, timeout, *args, **kwargs)

    wrap_function_wrapper(module, object_path, _call_wrapper)


def wrap_future(module, object_path, prepare, method):

    def _future_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        guid = '%016x' % random.getrandbits(64)
        uri = _get_uri(instance)

        request, timeout, args, kwargs = prepare(
                transaction, guid, *args, **kwargs)
        future = wrapped(request, timeout, *args, **kwargs)
        future._nr_guid = guid
        future._nr_args = (transaction, 'gRPC', uri, method)
        future._nr_start_time = time.time()

        # In non-streaming responses, result is typically called instead of
        # using the iterator. In streaming calls, the iterator is typically
        # used.

        return future

    wrap_function_wrapper(module, object_path, _future_wrapper)


def wrap_next(_wrapped, _instance, _args, _kwargs):
    _nr_args = getattr(_instance, '_nr_args', None)
    if not _nr_args:
        return _wrapped(*_args, **_kwargs)

    try:
        return _wrapped(*_args, **_kwargs)
    except Exception:
        delattr(_instance, '_nr_args')
        _nr_start_time = getattr(_instance, '_nr_start_time', 0.0)
        _nr_guid = getattr(_instance, '_nr_guid', None)

        with ExternalTrace(*_nr_args) as t:
            t.start_time = _nr_start_time or t.start_time
            t.guid = _nr_guid or t.guid
            raise


def wrap_result(_wrapped, _instance, _args, _kwargs):
    _nr_args = getattr(_instance, '_nr_args', None)
    if not _nr_args:
        return _wrapped(*_args, **_kwargs)
    delattr(_instance, '_nr_args')
    _nr_start_time = getattr(_instance, '_nr_start_time', 0.0)
    _nr_guid = getattr(_instance, '_nr_guid', None)

    try:
        result = _wrapped(*_args, **_kwargs)
    except Exception:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _nr_start_time or t.start_time
            t.guid = _nr_guid or t.guid
            raise
    else:
        with ExternalTrace(*_nr_args) as t:
            t.start_time = _nr_start_time or t.start_time
            t.guid = _nr_guid or t.guid
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


def _trailing_metadata(state, *args, **kwargs):
    return state.trailing_metadata


def _nr_wrap_status_code(wrapped, instance, args, kwargs):
    status_code = wrapped(*args, **kwargs)
    response_headers = _trailing_metadata(*args, **kwargs)

    transaction = current_transaction()
    if transaction:
        transaction.process_response(status_code, response_headers)

    return status_code


def _nr_wrap_abort(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction:
        transaction.record_exception()

    return wrapped(*args, **kwargs)


def instrument_grpc__channel(module):
    wrap_call(module, '_UnaryUnaryMultiCallable.__call__',
            _prepare_request, 'unary_unary')
    wrap_call(module, '_UnaryUnaryMultiCallable.with_call',
            _prepare_request, 'unary_unary')
    wrap_future(module, '_UnaryUnaryMultiCallable.future',
            _prepare_request, 'unary_unary')
    wrap_future(module, '_UnaryStreamMultiCallable.__call__',
            _prepare_request, 'unary_stream')
    wrap_call(module, '_StreamUnaryMultiCallable.__call__',
            _prepare_request_stream, 'stream_unary')
    wrap_call(module, '_StreamUnaryMultiCallable.with_call',
            _prepare_request_stream, 'stream_unary')
    wrap_future(module, '_StreamUnaryMultiCallable.future',
            _prepare_request_stream, 'stream_unary')
    wrap_future(module, '_StreamStreamMultiCallable.__call__',
            _prepare_request_stream, 'stream_stream')
    wrap_function_wrapper(module, '_Rendezvous._next',
            wrap_next)
    wrap_function_wrapper(module, '_Rendezvous.result',
            wrap_result)
    wrap_function_wrapper(module, '_Rendezvous.cancel',
            wrap_result)


def instrument_grpc_server(module):
    wrap_function_wrapper(module, '_unary_response_in_pool',
            grpc_web_transaction)
    wrap_function_wrapper(module, '_stream_response_in_pool',
            grpc_web_transaction)
    wrap_function_wrapper(module, '_completion_code',
            _nr_wrap_status_code)
    wrap_function_wrapper(module, '_abortion_code',
            _nr_wrap_status_code)
    wrap_function_wrapper(module, '_abort',
            _nr_wrap_abort)
