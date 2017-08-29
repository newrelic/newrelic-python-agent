import time

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper)


def _get_uri(instance, *args, **kwargs):
    target = instance._channel.target().decode('utf-8')
    method = instance._method.decode('utf-8').lstrip('/')
    return 'grpc://%s/%s' % (target, method)


def wrap_external_call(module, object_path, library, url, method=None):
    def _wrap_call(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        import grpc

        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)
        else:
            _url = url

        _start = time.time()

        try:
            result = wrapped(*args, **kwargs)
        except grpc.RpcError:
            with ExternalTrace(transaction, library, _url, method) as t:
                t.start_time = _start
                raise
        else:
            with ExternalTrace(transaction, library, _url, method) as t:
                t.start_time = _start
                return result

    wrap_function_wrapper(module, object_path, _wrap_call)


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

        @function_wrapper
        def wrap_next(_wrapped, _instance, _args, _kwargs):
            import grpc

            _start = time.time()
            try:
                result = _wrapped(*_args, **_kwargs)
            except StopIteration:
                raise
            except grpc.RpcError as e:
                if hasattr(e, 'cancelled') and e.cancelled():
                    raise
                else:
                    with ExternalTrace(
                            transaction, library, _url, method) as t:
                        t.start_time = _start
                        raise
            else:
                with ExternalTrace(transaction, library, _url, method) as t:
                    t.start_time = _start
                    return result

        future = wrapped(*args, **kwargs)
        future._next = wrap_next(future._next)

        return future

    wrap_function_wrapper(module, object_path, _wrap_future)


def _nr_wrap_GeneratedProtocolMessageType(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    instance.SerializeToString = FunctionTraceWrapper(
            instance.SerializeToString)
    instance.FromString = staticmethod(FunctionTraceWrapper(
            instance.FromString))


def instrument_grpc__channel(module):
    wrap_external_call(module, '_UnaryUnaryMultiCallable.__call__',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_call(module, '_UnaryUnaryMultiCallable.with_call',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_future(module, '_UnaryUnaryMultiCallable.future',
            'gRPC', _get_uri, 'unary_unary')
    wrap_external_future(module, '_UnaryStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'unary_stream')
    wrap_external_call(module, '_StreamUnaryMultiCallable.__call__',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_call(module, '_StreamUnaryMultiCallable.with_call',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_future(module, '_StreamUnaryMultiCallable.future',
            'gRPC', _get_uri, 'stream_unary')
    wrap_external_future(module, '_StreamStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'stream_stream')


def instrument_google_protobuf_reflection(module):
    wrap_function_wrapper(module, 'GeneratedProtocolMessageType.__init__',
            _nr_wrap_GeneratedProtocolMessageType)
