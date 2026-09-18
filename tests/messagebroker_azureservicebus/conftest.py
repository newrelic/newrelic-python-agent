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

import os
import pytest

from testing_support.db_settings import servicebus_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.util import instance_hostname

from newrelic.common.package_version_utils import get_package_version_tuple

PIKA_VERSION_INFO = get_package_version_tuple("azure.servicebus")
DB_SETTINGS = servicebus_settings()


_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (messagebroker_servicebus)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (messagebroker_servicebus)"],
)


#------------------
# Sync Services
#------------------

@pytest.fixture
def service_bus_client():
    from azure.servicebus.management import ServiceBusAdministrationClient
    from azure.servicebus import ServiceBusClient

    admin_connection_string = DB_SETTINGS.get("admin_connection_string")
    connection_string = DB_SETTINGS.get("connection_string")
    host = DB_SETTINGS.get("host")
    admin_port = DB_SETTINGS.get("admin_port")

    with ServiceBusAdministrationClient.from_connection_string(admin_connection_string) as admin_client:
        # Override the base URL to point to the emulator's admin API endpoint
        admin_client._impl._client._base_url = f"http://{host}:{admin_port}"

        queue_name = f"queue-{os.getpid()}"
        topic_name = f"topic-{os.getpid()}"
        subscription_name = f"subscription-{os.getpid()}"
        try:
            admin_client.create_queue(queue_name)
            admin_client.create_topic(topic_name)
            admin_client.create_subscription(topic_name, subscription_name)

            with ServiceBusClient.from_connection_string(connection_string) as client:
                yield (client, queue_name, topic_name, subscription_name)

        finally:
            try:
                admin_client.delete_queue(queue_name)
                admin_client.delete_subscription(topic_name, subscription_name)
                admin_client.delete_topic(topic_name)
            except Exception:
                raise


@pytest.fixture
def client(service_bus_client):
    client, _, _, _ = service_bus_client
    return client


@pytest.fixture
def queue_name(service_bus_client):
    _, queue_name, _, _ = service_bus_client
    return queue_name


@pytest.fixture
def topic_name(service_bus_client):
    _, _, topic_name, _ = service_bus_client
    return topic_name


@pytest.fixture
def subscription_name(service_bus_client):
    _, _, _, subscription_name = service_bus_client
    return subscription_name


@pytest.fixture
def queue_sender(client, queue_name):
    with client.get_queue_sender(queue_name=queue_name) as queue_sender:
        yield queue_sender


@pytest.fixture
def topic_sender(client, topic_name):
    with client.get_topic_sender(topic_name=topic_name) as topic_sender:
        yield topic_sender


@pytest.fixture
def queue_receiver(client, queue_name):
    with client.get_queue_receiver(queue_name=queue_name) as queue_receiver:
        yield queue_receiver


@pytest.fixture
def queue_dead_letter_receiver(client, queue_name):
    from azure.servicebus import ServiceBusSubQueue

    with client.get_queue_receiver(queue_name=queue_name, sub_queue=ServiceBusSubQueue.DEAD_LETTER) as queue_dead_letter_receiver:
        yield queue_dead_letter_receiver


@pytest.fixture
def subscription_receiver(client, topic_name, subscription_name):
    with client.get_subscription_receiver(topic_name=topic_name, subscription_name=subscription_name) as subscription_receiver:
        yield subscription_receiver


@pytest.fixture
def subscription_dead_letter_receiver(client, topic_name, subscription_name):
    from azure.servicebus import ServiceBusSubQueue

    with client.get_subscription_receiver(topic_name=topic_name, subscription_name=subscription_name, sub_queue=ServiceBusSubQueue.DEAD_LETTER) as subscription_dead_letter_receiver:
        yield subscription_dead_letter_receiver


