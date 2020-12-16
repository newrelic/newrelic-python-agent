from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper
from validate_distributed_tracing_header import \
    validate_distributed_tracing_header
from validate_outbound_headers import validate_outbound_headers


@function_wrapper
def validate_cross_process_headers(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    transaction = current_transaction()
    settings = transaction.settings

    if settings.distributed_tracing.enabled:
        validate_distributed_tracing_header()
    else:
        validate_outbound_headers()

    return result
