from minversion import pika_version_info


def basic_consume(channel, queue, callback, auto_ack=None):
    kwargs = {'queue': queue}
    if pika_version_info[0] < 1:
        kwargs['consumer_callback'] = callback
        if auto_ack is not None:
            kwargs['no_ack'] = not auto_ack
    else:
        kwargs['on_message_callback'] = callback
        if auto_ack is not None:
            kwargs['auto_ack'] = auto_ack

    return channel.basic_consume(**kwargs)
