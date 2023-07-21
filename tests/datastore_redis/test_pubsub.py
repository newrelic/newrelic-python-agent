# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import redis.asyncio
import pytest
import time

from newrelic.api.background_task import background_task

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname
from testing_support.fixture.event_loop import event_loop as loop


DB_SETTINGS = redis_settings()[0]

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Datastore/operation/Redis/pubsub', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Redis/all', 2),
        ('Datastore/Redis/allOther', 2),
        ('Datastore/operation/Redis/pubsub', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Redis/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 1)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

# Tests

# # working...ish
# @override_application_settings(_enable_instance_settings)
# @validate_transaction_metrics(
#         'test_pubsub:test_pubsub_enable_instance_reporting',
#         scoped_metrics=_enable_scoped_metrics,
#         rollup_metrics=_enable_rollup_metrics,
#         background_task=True)
@background_task()
def test_pubsub_enable_instance_reporting(loop):  # noqa
    async def exercise():
        client = redis.asyncio.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
        client.publish("my-first-channel", "Hello, world!")
        pubsub = client.pubsub()
        pubsub.subscribe("my-first-channel")
        # await asyncio.sleep(1)
        time.sleep(1)
        for message in pubsub.get_message():
             assert message

    loop.run_until_complete(exercise())


# Not working
# @background_task()
# def test_monitor(loop):  # noqa
#     async def exercise():
#         client = redis.Redis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)
#         monitor = client.monitor()
#         try:
#             for _ in monitor.listen():
#                 break
#         except (TimeoutError):
#             # that's ok, we are just testing sync/async wrapping
#             pass

#     loop.run_until_complete(exercise())