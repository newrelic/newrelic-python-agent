import gc
import pika

from newrelic.api.background_task import background_task
from testing_support.db_settings import rabbitmq_settings


DB_SETTINGS = rabbitmq_settings()[0]


#@background_task()
#def test_memory_leak():
#    params = pika.ConnectionParameters(
#            DB_SETTINGS['host'], DB_SETTINGS['port'])

#    # create 2 unreferenced blocking channels
#    with pika.BlockingConnection(params) as connection:
#        for _ in range(2):
#            connection.channel().basic_publish(
#                    exchange='', routing_key='memory_leak_test', body='test')

#    # garbage collect until everything is reachable
#    while gc.collect():
#        pass

    # the number of channel objects stored should be 0
#    from pika.adapters.blocking_connection import BlockingChannel
#    channel_objects_stored = sum(1 for o in gc.get_objects()
#            if isinstance(o, BlockingChannel))

#    assert channel_objects_stored == 0
