import warnings

import newrelic.api.transaction_name

#warnings.warn('API change. Use transaction_name module instead of '
#       'name_transaction module.', DeprecationWarning, stacklevel=2)

NameTransactionWrapper = newrelic.api.transaction_name.TransactionNameWrapper
name_transaction = newrelic.api.transaction_name.transaction_name
wrap_name_transaction = newrelic.api.transaction_name.wrap_transaction_name
