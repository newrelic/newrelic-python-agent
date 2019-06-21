import inspect
import logging
import newrelic.packages.six as six

from newrelic.common.object_wrapper import ObjectProxy

_logger = logging.getLogger(__name__)

CancelledError = None

if hasattr(inspect, 'iscoroutinefunction'):
    def is_coroutine_function(wrapped):
        return inspect.iscoroutinefunction(wrapped)
else:
    def is_coroutine_function(wrapped):
        return False


if six.PY3:
    def is_asyncio_coroutine(wrapped):
        """Return True if func is a decorated coroutine function."""
        return getattr(wrapped, '_is_coroutine', None) is not None
else:
    def is_asyncio_coroutine(wrapped):
        return False


def is_generator_function(wrapped):
    return inspect.isgeneratorfunction(wrapped)


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, '__tornado_coroutine__')


class TraceContext(object):
    # Assumption made for this context manager: no other object maintains a
    # reference to trace after the TraceContext is constructed.
    # This is important because the assumption made by the logic below is that
    # only the TraceContext object can call __enter__ on the trace (which may
    # delete the transaction).

    def __init__(self, trace):
        if not trace.transaction:
            self.trace = None
        else:
            self.trace = trace

        self.current_trace = None

    def pre_close(self):
        pass

    def close(self):
        if self.trace:
            self.trace.__exit__(None, None, None)
            self.trace = None

    def __enter__(self):
        if not self.trace:
            return self

        self.current_trace = self.trace.transaction.current_span
        if not self.trace.activated:
            self.trace.__enter__()

            # Transaction can be cleared by calling enter (such as when tracing
            # as a child of a terminal node)
            # In this case, we clear out the transaction and defer to the
            # wrapped function
            if not self.trace.transaction:
                self.trace = None
        else:
            # In the case that the function trace is already active, notify the
            # transaction that this coroutine is now the current node (for
            # automatic parenting)
            self.trace.transaction.current_span = self.trace

        return self

    def __exit__(self, exc, value, tb):
        if not self.trace:
            return

        txn = self.trace.transaction

        # If the current node has been changed, record this as an error in a
        # supportability metric.
        if txn.current_span is not self.trace:
            txn.record_custom_metric(
                    'Supportability/Python/TraceContext/ExitNodeMismatch',
                    {'count': 1})
            _logger.debug('Trace context exited with an unexpected current '
                    'node. Current trace is %r. Expected trace is %r. '
                    'Please report this issue to New Relic Support.',
                    self.current_trace, self.trace)

        if exc in (StopIteration, GeneratorExit):
            self.trace.__exit__(None, None, None)
            self.trace = None
        elif exc:
            self.trace.__exit__(exc, value, tb)
            self.trace = None

        # Since the coroutine is returning control to the parent at this
        # point, we should notify the transaction that this coroutine is no
        # longer the current node for parenting purposes
        if self.current_trace:
            txn.current_span = self.current_trace

            # Clear out the current trace so that it cannot be reused in future
            # exits and doesn't maintain a dangling reference to a trace.
            self.current_trace = None

    def __del__(self):
        # If the trace goes out of scope, it's possible it's still active.
        # It's important that we end the trace so that the trace is reported.
        # It's also important that we don't change the current node as part of
        # this reporting.
        if self.trace and self.trace.activated:
            txn = self.trace.transaction
            if txn:
                current_trace = txn.current_span
                self.trace.__exit__(None, None, None)
                if current_trace is not self.trace:
                    txn.current_span = current_trace


class TransactionContext(object):
    def __init__(self, transaction):
        self.transaction = transaction
        if not self.transaction.enabled:
            self.transaction = None

    def pre_close(self):
        if self.transaction and not self.transaction._state:
            self.transaction = None

    def close(self):
        if not self.transaction:
            return

        if self.transaction._state:
            try:
                with self:
                    raise GeneratorExit
            except GeneratorExit:
                pass

    def __enter__(self):
        if not self.transaction:
            return self

        if not self.transaction._state:
            self.transaction.__enter__()
        elif self.transaction.enabled:
            self.transaction.save_transaction()

        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return

        global CancelledError

        if CancelledError is None:
            try:
                from concurrent.futures import CancelledError
            except:
                CancelledError = GeneratorExit

        # case: coroutine completed or cancelled
        if (exc is StopIteration or exc is GeneratorExit or
                exc is CancelledError):
            self.transaction.__exit__(None, None, None)

        # case: coroutine completed because of error
        elif exc:
            self.transaction.__exit__(exc, value, tb)

        # case: coroutine suspended but not completed
        elif self.transaction.enabled:
            self.transaction.drop_transaction()


class Coroutine(ObjectProxy):
    def __init__(self, wrapped, context):
        super(Coroutine, self).__init__(wrapped)
        self._nr_context = context

    def send(self, value):
        with self._nr_context:
            return self.__wrapped__.send(value)

    def throw(self, *args, **kwargs):
        with self._nr_context:
            return self.__wrapped__.throw(*args, **kwargs)

    def close(self):
        self._nr_context.pre_close()

        try:
            with self._nr_context:
                result = self.__wrapped__.close()
        except:
            raise

        self._nr_context.close()
        return result


class GeneratorProxy(Coroutine):
    def __iter__(self):
        return self

    if six.PY2:
        def next(self):
            return self.send(None)
    else:
        def __next__(self):
            return self.send(None)


class AwaitableGeneratorProxy(GeneratorProxy):
    def __await__(self):
        return self


class CoroutineProxy(Coroutine):
    def __await__(self):
        return GeneratorProxy(self.__wrapped__, self._nr_context)


def async_proxy(wrapped):
    if is_coroutine_function(wrapped):
        return CoroutineProxy
    elif is_generator_function(wrapped):
        if is_asyncio_coroutine(wrapped):
            return AwaitableGeneratorProxy
        else:
            return GeneratorProxy
