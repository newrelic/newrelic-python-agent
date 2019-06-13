from newrelic.common.object_wrapper import wrap_out_function
from newrelic.core.transaction_cache import transaction_cache


def propagate_task_context(task):
    cache = transaction_cache()
    transaction = cache.current_transaction()
    if transaction:
        cache._cache[id(task)] = transaction
    return task


def instrument_asyncio_base_events(module):
    wrap_out_function(
            module,
            'BaseEventLoop.create_task',
            propagate_task_context)
