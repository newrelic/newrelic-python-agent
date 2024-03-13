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

import io
import json
import os
import re

import pytest
from _mock_external_bedrock_server import (
    MockExternalBedrockServer,
    extract_shortened_prompt,
)
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import (
    get_package_version,
    get_package_version_tuple,
)
from newrelic.common.signature import bind_args

BOTOCORE_VERSION = get_package_version("botocore")

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "custom_insights_events.max_attribute_value": 4096,
    "ai_monitoring.enabled": True,
}
collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (external_botocore)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (external_botocore)"],
)


# Bedrock Fixtures

BEDROCK_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "bedrock_audit.log")
BEDROCK_AUDIT_LOG_CONTENTS = {}

disabled_ai_monitoring_settings = override_application_settings({"ai_monitoring.enabled": False})
disabled_ai_monitoring_record_content_settings = override_application_settings(
    {"ai_monitoring.record_content.enabled": False}
)

# Token callback test functions
def llm_token_count_callback_success(model, content):
    return 105


def llm_token_count_callback_negative_return_val(model, content):
    return -3


def llm_token_count_callback_non_int_return_val(model, content):
    return "python"


@pytest.fixture(scope="session")
def bedrock_server():
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real Bedrock backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_BEDROCK_RESPONSES=1 as
    an environment variable to run using the real Bedrock backend. (Default: mocking)
    """
    import boto3

    from newrelic.core.config import _environ_as_bool

    if get_package_version_tuple("botocore") < (1, 31, 57):
        pytest.skip(reason="Bedrock Runtime not available.")

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_BEDROCK_RESPONSES", False):
        # Use mocked Bedrock backend and prerecorded responses
        with MockExternalBedrockServer() as server:
            client = boto3.client(  # nosec
                "bedrock-runtime",
                "us-east-1",
                endpoint_url="http://localhost:%d" % server.port,
                aws_access_key_id="NOT-A-REAL-SECRET",
                aws_secret_access_key="NOT-A-REAL-SECRET",
            )

            yield client
    else:
        # Use real Bedrock backend and record responses
        assert (
            os.environ["AWS_ACCESS_KEY_ID"] and os.environ["AWS_SECRET_ACCESS_KEY"]
        ), "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required."

        # Construct real client
        client = boto3.client(
            "bedrock-runtime",
            "us-east-1",
        )

        # Apply function wrappers to record data
        wrap_function_wrapper(
            "botocore.endpoint", "Endpoint._do_get_response", wrap_botocore_endpoint_Endpoint__do_get_response
        )
        wrap_function_wrapper(
            "botocore.eventstream",
            "EventStreamBuffer.add_data",
            wrap_botocore_eventstream_add_data,
        )
        yield client  # Run tests

        # Write responses to audit log
        bedrock_audit_log_contents = dict(sorted(BEDROCK_AUDIT_LOG_CONTENTS.items(), key=lambda i: (i[1][1], i[0])))
        with open(BEDROCK_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(bedrock_audit_log_contents, fp=audit_log_fp, indent=4)


# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = set(["x-amzn-requestid", "x-amzn-errortype", "content-type"])


def wrap_botocore_endpoint_Endpoint__do_get_response(wrapped, instance, args, kwargs):
    request = bind__do_get_response(*args, **kwargs)
    if not request:
        return wrapped(*args, **kwargs)

    match = re.search(r"/model/([0-9a-zA-Z.-]+)/", request.url)
    model = match.group(1)

    # Send request
    result = wrapped(*args, **kwargs)

    # Unpack response
    success, exception = result
    response = (success or exception)[0]

    try:
        if isinstance(request.body, io.BytesIO):
            request.body.seek(0)
            body = json.loads(request.body.read())
        else:
            body = json.loads(request.body)
    except Exception:
        body = {}

    prompt = extract_shortened_prompt(body, model)
    headers = dict(response.headers.items())
    headers = dict(
        filter(
            lambda k: k[0].lower() in RECORDED_HEADERS or k[0].startswith("x-ratelimit"),
            headers.items(),
        )
    )
    status_code = response.status_code

    # Log response
    if response.raw.chunked:
        # Log response
        BEDROCK_AUDIT_LOG_CONTENTS[prompt] = headers, status_code, []  # Append response data to audit log
    else:
        # Clean up data
        data = json.loads(response.content.decode("utf-8"))
        BEDROCK_AUDIT_LOG_CONTENTS[prompt] = headers, status_code, data  # Append response data to audit log
    return result


def bind__do_get_response(request, operation_model, context):
    return request


@pytest.fixture(scope="session")
def set_trace_info():
    def _set_trace_info():
        txn = current_transaction()
        if txn:
            txn.guid = "transaction-id"
            txn._trace_id = "trace-id"

    return _set_trace_info


def wrap_botocore_eventstream_add_data(wrapped, instance, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)
    data = bound_args["data"].hex()  # convert bytes to hex for storage
    prompt = [k for k in BEDROCK_AUDIT_LOG_CONTENTS.keys()][-1]
    BEDROCK_AUDIT_LOG_CONTENTS[prompt][2].append(data)
    return wrapped(*args, **kwargs)
