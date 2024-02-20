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

import json
import os
from time import sleep

import pytest
from _mock_external_pinecone_server import (  # noqa: F401; pylint: disable=W0611
    MockExternalPineconeServer,
    extract_shortened_prompt,
    simple_get,
)
from pinecone import Pinecone, PodSpec
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

PINECONE_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "pinecone_audit.log")
PINECONE_AUDIT_LOG_CONTENTS = {}

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_explain_plan_queries": True,
    "ml_insights_events.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_pinecone)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


@pytest.fixture(scope="function")
def pinecone_clients(MockExternalPineconeServer):  # noqa: F811
    # def pinecone_client():  # noqa: F811
    """
    This configures the pinecone client.
    """
    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_PINECONE_RESPONSES", False):
        with MockExternalPineconeServer():
            pinecone = Pinecone(
                api_key="NOT-A-REAL-SECRET",
            )
            yield pinecone
    else:
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        if not pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY environment variable required.")

        pinecone = Pinecone(
            api_key=pinecone_api_key,
        )
        yield pinecone


# @pytest.fixture(autouse=True, scope="session")
@pytest.fixture(autouse=True, scope="function")
def pinecone_server(
    pinecone_clients,
    wrap_client_api_client_call_api,
):
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real Pinecone backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_PINECONE_RESPONSES=1 as
    an environment variable to run using the real Pinecone backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_PINECONE_RESPONSES", False):
        # Apply function wrappers to record data
        wrap_function_wrapper("pinecone.core.client.api_client", "ApiClient.call_api", wrap_client_api_client_call_api)
        yield  # Run tests
        # Write responses to audit log
        with open(PINECONE_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(PINECONE_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        # We are mocking Pinecone responses so we don't need to do anything in this case.
        yield


def bind_call_api(resource_path, method, path_params, query_params, header_params, body, *args, **kwargs):
    return header_params, body


@pytest.fixture(scope="function")
def wrap_client_api_client_call_api():
    def _wrap_client_api_client_call_api(wrapped, instance, args, kwargs):
        header_params, request = bind_call_api(*args, **kwargs)
        if not request:
            return wrapped(*args, **kwargs)

        request_log = str((type(request).__name__, request.to_str()[:50]))
        response = wrapped(*args, **kwargs)

        if hasattr(response, "to_dict"):
            response_log = response.to_dict()
        else:
            response_log = response.__str__()

        PINECONE_AUDIT_LOG_CONTENTS[request_log] = header_params, response_log  # Append response data to log

        return response

    return _wrap_client_api_client_call_api


@pytest.fixture(scope="function")
def pinecone_instance(pinecone_clients):
    # Delete if already exists/did not get properly deleted
    # from previous runs
    if len(pinecone_clients.list_indexes()) > 1:
        pinecone_clients.delete_index("python-test")

    pinecone_clients.create_index(
        name="python-test",
        dimension=4,
        metric="cosine",
        spec=PodSpec(
            environment="us-east-1-aws",
            pod_type="p1.x1",
            pods=1,
        ),
    )

    yield pinecone_clients
    pinecone_clients.delete_index("python-test")


@pytest.fixture(scope="function")
def pinecone_index_instance(pinecone_instance):
    index = pinecone_instance.Index("python-test")
    sleep(2)
    yield index
    index.delete("python-test")


@pytest.fixture
def set_trace_info():
    def set_info():
        txn = current_transaction()
        if txn:
            txn.guid = "transaction-id"
            txn._trace_id = "trace-id"

    return set_info
