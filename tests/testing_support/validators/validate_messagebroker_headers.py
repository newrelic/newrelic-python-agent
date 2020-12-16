from newrelic.common.object_wrapper import function_wrapper
from newrelic.api.transaction import current_transaction
from testing_support.external_fixtures import (
        validate_distributed_tracing_header,
        validate_outbound_headers)

@function_wrapper
def validate_messagebroker_headers(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    transaction = current_transaction()
    settings = transaction.settings

    if settings.distributed_tracing.enabled:
        validate_distributed_tracing_header()
    else:
        validate_outbound_headers(header_id='NewRelicID',
                header_transaction='NewRelicTransaction')

    return result

