import time

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.messagebroker_trace import wrap_messagebroker_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper


def _nr_wrapper_BlockingChannel_basic_consume_(wrapped, instance, args,
        kwargs):

    def _bind_params(consumer_callback, *args, **kwargs):
        return consumer_callback

    transaction = current_transaction(active_only=False)
    callback = _bind_params(*args, **kwargs)
    name = callable_name(callback)

    # A consumer callback can be called either outside of a transaction, or
    # within the context of an existing transaction. There are 3 possibilities
    # we need to handle: (Note that this is similar to our Celery
    # instrumentation)
    #
    #   1. In an inactive transaction
    #
    #      If the end_of_transaction() or ignore_transaction() API calls
    #      have been invoked, this task may be called in the context
    #      of an inactive transaction. In this case, don't wrap the task
    #      in any way. Just run the original function.
    #
    #   2. In an active transaction
    #
    #      Run the original function inside a MessageBrokerTrace.
    #
    #   3. Outside of a transaction
    #
    #      Since it's not running inside of an existing transaction, we want to
    #      create a new background transaction for it.

    if transaction and (transaction.ignore_transaction or transaction.stopped):
        return wrapped(*args, **kwargs)

    elif transaction:
        def wrapped_callback(*args, **kwargs):
            with FunctionTrace(transaction=transaction, name=name):
                return callback(*args, **kwargs)

    else:
        # TODO: Replace with destination type/name
        bt_group = 'Message/RabbitMQ/None'
        bt_name = 'Named/None'

        def wrapped_callback(*args, **kwargs):
            with BackgroundTask(application=application_instance(),
                    name=bt_name, group=bt_group) as bt:
                with FunctionTrace(transaction=bt, name=name):
                    return callback(*args, **kwargs)

    if len(args) > 0:
        args = list(args)
        args[0] = wrapped_callback
    else:
        kwargs['consumer_callback'] = wrapped_callback

    return wrapped(*args, **kwargs)


def _nr_wrapper_Basic_Deliver_init_(wrapper, instance, args, kwargs):
    ret = wrapper(*args, **kwargs)
    instance._nr_start_time = time.time()
    return ret


def instrument_pika_connection(module):
    wrap_messagebroker_trace(module.Connection, '_send_message',
            product='RabbitMQ', target=None, operation='Produce')


def instrument_pika_adapters(module):
    wrap_function_wrapper(module.blocking_connection,
            'BlockingChannel.basic_consume',
            _nr_wrapper_BlockingChannel_basic_consume_)


def instrument_pika_spec(module):
    wrap_function_wrapper(module.Basic.Deliver, '__init__',
            _nr_wrapper_Basic_Deliver_init_)
