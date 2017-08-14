import sys
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace


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

        trace = ExternalTrace(transaction, library, _url, method)
        trace.__enter__()

        # There are no children of an external, ever!
        transaction._pop_current(trace)

        future = wrapped(*args, **kwargs)

        def _future_done(f):
            try:
                f.result()
                trace.__exit__(None, None, None)
            except Exception:
                trace.__exit__(*sys.exc_info())

        future.add_done_callback(_future_done)

        return future

    wrap_function_wrapper(module, object_path, _wrap_future)


def instrument_grpc__channel(module):
    wrap_external_future(module, '_UnaryUnaryMultiCallable.future',
            'gRPC', _get_uri, 'unary_unary')

    wrap_external_future(module, '_StreamUnaryMultiCallable.future',
            'gRPC', _get_uri, 'stream_unary')

    wrap_external_future(module, '_UnaryStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'unary_stream')

    wrap_external_future(module, '_StreamStreamMultiCallable.__call__',
            'gRPC', _get_uri, 'stream_stream')
