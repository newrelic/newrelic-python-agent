from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper)
from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import (ExternalTrace, wrap_external_trace)


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

        @function_wrapper
        def wrap_next(_wrapped, _instance, _args, _kwargs):
            if not _instance._state.code:
                with ExternalTrace(transaction, library, _url, method):
                    return _wrapped(*_args, **_kwargs)
            else:
                return _wrapped(*_args, **_kwargs)

        future = wrapped(*args, **kwargs)
        future._next = wrap_next(future._next)

        return future

    wrap_function_wrapper(module, object_path, _wrap_future)


def _nr_add_cat_value_(wrapped, instance, args, kwargs):
    def _bind_params(application_metadata):
        return application_metadata

    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    metadata = _bind_params(*args, **kwargs)

    cat_value = ExternalTrace.get_request_metadata(transaction)
    if cat_value:
        metadata = metadata and list(metadata) or []

        # Do not overwrite if headers are already set
        for k, v in metadata:
            if k == ExternalTrace.cat_metadata_key:
                return wrapped(*args, **kwargs)

        metadata.append((ExternalTrace.cat_metadata_key, cat_value))

    return wrapped(metadata)


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


def instrument_grpc_common(module):
    wrap_function_wrapper(module, 'to_cygrpc_metadata',
            _nr_add_cat_value_)
