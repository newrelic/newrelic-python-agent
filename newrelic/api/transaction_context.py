import warnings
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy


class TransactionContext(object):
    show_warning = True

    def __init__(self, transaction):
        self.transaction = transaction
        if transaction:
            self.trace = transaction.current_span
        self.restore_transaction = None
        self.restore_trace = None

        if self.show_warning:
            warnings.warn((
                'The TransactionContext API has been deprecated and will be '
                'removed in a future release.'
            ), DeprecationWarning)

    def __enter__(self):
        self.restore_transaction = current_transaction(active_only=False)

        if self.restore_transaction:
            self.restore_transaction.drop_transaction()

        # If transaction has exited, do not restore
        if self.transaction and self.transaction.enabled:
            self.transaction.save_transaction()
            self.restore_trace = self.transaction.current_span
            self.transaction.current_span = self.trace

        return self

    def __exit__(self, exc, value, tb):
        if self.transaction:
            # only restore if the trace is not already exited
            if self.restore_trace and not self.restore_trace.exited:
                self.transaction.current_span = self.restore_trace
            current = current_transaction(active_only=False)
            if current is self.transaction:
                self.transaction.drop_transaction()

        # Only restore transactions that have not exited
        if self.restore_transaction and self.restore_transaction.enabled:
            self.restore_transaction.save_transaction()


class _TransactionContext(TransactionContext):
    show_warning = False


class CoroutineTransactionContext(ObjectProxy):
    def __init__(self, coro, transaction):

        self._nr_transaction_context = _TransactionContext(transaction)

        # Wrap the coroutine
        super(CoroutineTransactionContext, self).__init__(coro)

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        return self.send(None)

    next = __next__

    def send(self, value):
        with self._nr_transaction_context:
            return self.__wrapped__.send(value)

    def throw(self, *args, **kwargs):
        with self._nr_transaction_context:
            return self.__wrapped__.throw(*args, **kwargs)

    def close(self):
        with self._nr_transaction_context:
            return self.__wrapped__.close()
