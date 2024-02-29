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

from newrelic.common.object_wrapper import wrap_function_wrapper

PINECONE_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "pinecone_audit.log")
PINECONE_AUDIT_LOG_CONTENTS = {}
RECORDED_HEADERS = set(["content-type"])

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
def pinecone_client(MockExternalPineconeServer):  # noqa: F811
    """
    This configures the pinecone client.
    """
    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_PINECONE_RESPONSES", False):
        with MockExternalPineconeServer() as server:
            pinecone = Pinecone(
                api_key="NOT-A-REAL-SECRET",
                host="http://localhost:%d" % server.port,
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


@pytest.fixture(autouse=True, scope="function")
def pinecone_server(
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


def bind_call_api(resource_path, method, path_params, query_params, header_params, *args, **kwargs):
    return resource_path, method


@pytest.fixture(scope="function")
def wrap_client_api_client_call_api():
    def _wrap_client_api_client_call_api(wrapped, instance, args, kwargs):
        resource_path, method = bind_call_api(*args, **kwargs)
        request_log = "%s %s" % (method, resource_path)
        response = wrapped(*args, **kwargs)

        response_headers = dict(instance.last_response.getheaders())

        headers = dict(
            filter(
                lambda k: k[0].lower() in RECORDED_HEADERS,
                response_headers.items(),
            )
        )
        response_status = instance.last_response.status

        if hasattr(response, "to_dict"):
            response_log = response.to_dict()
        else:
            response_log = response.__str__()

        PINECONE_AUDIT_LOG_CONTENTS[request_log] = headers, response_status, response_log  # Append response data to log

        return response

    return _wrap_client_api_client_call_api


@pytest.fixture(scope="function")
def pinecone_instance(pinecone_client):
    # Delete if already exists/did not get properly deleted
    # from previous runs
    if "python-test" in pinecone_client.list_indexes().names():
        pinecone_client.delete_index("python-test")

    # breakpoint()
    pinecone_client.create_index(
        name="python-test",
        dimension=4,
        metric="cosine",
        spec=PodSpec(
            environment="us-east-1-aws",
            pod_type="p1.x1",
            pods=1,
        ),
    )
    # Have status be ready in mock server.  This will result in this while
    # loop being skipped over during the mock server execution of this
    while not pinecone_client.describe_index("python-test")["status"]["ready"]:
        sleep(1)

    yield pinecone_client
    pinecone_client.delete_index("python-test")


@pytest.fixture(scope="function")
def pinecone_index_instance(pinecone_instance):
    index = pinecone_instance.Index("python-test")
    sleep(3)
    yield index
    index.delete("python-test")


# @pytest.fixture
# def set_trace_info():
#     def set_info():
#         txn = current_transaction()
#         if txn:
#             txn.guid = "transaction-id"
#             txn._trace_id = "trace-id"

#     return set_info
