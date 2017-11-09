from newrelic.api.transaction import current_transaction


class TransactionContext(object):

    def __init__(self, transaction):
        self.transaction = transaction
        self.restore_transaction = None

    def __enter__(self):
        self.restore_transaction = current_transaction(active_only=False)

        if self.restore_transaction:
            self.restore_transaction.drop_transaction()

        if self.transaction:
            self.transaction.save_transaction()

    def __exit__(self, exc, value, tb):
        if self.transaction:
            current = current_transaction(active_only=False)
            if current is self.transaction:
                self.transaction.drop_transaction()

        if self.restore_transaction:
            self.restore_transaction.save_transaction()
