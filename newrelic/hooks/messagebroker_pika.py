from newrelic.api.messagebroker_trace import wrap_messagebroker_trace


def instrument_pika_connection(module):
    wrap_messagebroker_trace(module.Connection, '_send_message',
            product='RabbitMQ', target=None, operation='Produce')
