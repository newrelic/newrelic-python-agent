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

import pytest
from _mock_external_openai_server import (
    MockExternalOpenAIServer,
    extract_shortened_prompt,
    get_openai_version,
    openai_version,
    simple_get,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.signature import bind_args

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_langchain)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_langchain)"],
)


OPENAI_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "openai_audit.log")
OPENAI_AUDIT_LOG_CONTENTS = {}
# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = set(["x-request-id", "content-type"])


@pytest.fixture(scope="session")
def openai_clients(openai_version, MockExternalOpenAIServer):  # noqa: F811
    """
    This configures the openai client and returns it for openai v1 and only configures
    openai for v0 since there is no client.
    """
    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        with MockExternalOpenAIServer() as server:
            chat = ChatOpenAI(base_url=f"http://localhost:{server.port}", api_key="NOT-A-REAL-SECRET", temperature=0.7)
            embeddings = OpenAIEmbeddings(
                openai_api_key="NOT-A-REAL-SECRET", openai_api_base=f"http://localhost:{server.port}"
            )
            yield chat, embeddings
    else:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
        chat = ChatOpenAI(api_key=openai_api_key)
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        yield chat, embeddings


@pytest.fixture(scope="session")
def embedding_openai_client(openai_clients):
    _, embedding_client = openai_clients
    return embedding_client


@pytest.fixture(scope="session")
def chat_openai_client(openai_clients):
    chat_client, _ = openai_clients
    return chat_client


@pytest.fixture(autouse=True, scope="session")
def openai_server(
    openai_version,  # noqa: F811
    openai_clients,
    wrap_httpx_client_send,
    wrap_stream_iter_events,
):
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real OpenAI backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES=1 as
    an environment variable to run using the real OpenAI backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        wrap_function_wrapper("httpx._client", "Client.send", wrap_httpx_client_send)
        wrap_function_wrapper("openai._streaming", "Stream._iter_events", wrap_stream_iter_events)
        yield  # Run tests
        # Write responses to audit log
        with open(OPENAI_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(OPENAI_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        # We are mocking openai responses so we don't need to do anything in this case.
        yield


@pytest.fixture(scope="session")
def wrap_httpx_client_send(extract_shortened_prompt):  # noqa: F811
    def _wrap_httpx_client_send(wrapped, instance, args, kwargs):
        bound_args = bind_args(wrapped, args, kwargs)
        stream = bound_args.get("stream", False)
        request = bound_args["request"]
        if not request:
            return wrapped(*args, **kwargs)

        params = json.loads(request.content.decode("utf-8"))
        prompt = extract_shortened_prompt(params)

        # Send request
        response = wrapped(*args, **kwargs)

        if response.status_code >= 400 or response.status_code < 200:
            prompt = "error"

        rheaders = getattr(response, "headers")

        headers = dict(
            filter(
                lambda k: k[0].lower() in RECORDED_HEADERS
                or k[0].lower().startswith("openai")
                or k[0].lower().startswith("x-ratelimit"),
                rheaders.items(),
            )
        )
        # Append response data to log
        if stream:
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = [headers, response.status_code, []]
            if prompt == "error":
                OPENAI_AUDIT_LOG_CONTENTS[prompt][2] = json.loads(response.read())
        else:
            body = json.loads(response.content.decode("utf-8"))
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = headers, response.status_code, body
        return response

    return _wrap_httpx_client_send


@pytest.fixture(scope="session")
def generator_proxy(openai_version):
    class GeneratorProxy(ObjectProxy):
        def __init__(self, wrapped):
            super(GeneratorProxy, self).__init__(wrapped)

        def __iter__(self):
            return self

        # Make this Proxy a pass through to our instrumentation's proxy by passing along
        # get attr and set attr calls to our instrumentation's proxy.
        def __getattr__(self, attr):
            return self.__wrapped__.__getattr__(attr)

        def __setattr__(self, attr, value):
            return self.__wrapped__.__setattr__(attr, value)

        def __next__(self):
            transaction = current_transaction()
            if not transaction:
                return self.__wrapped__.__next__()

            try:
                return_val = self.__wrapped__.__next__()
                if return_val:
                    prompt = [k for k in OPENAI_AUDIT_LOG_CONTENTS.keys()][-1]
                    if openai_version < (1, 0):
                        headers = dict(
                            filter(
                                lambda k: k[0].lower() in RECORDED_HEADERS
                                or k[0].lower().startswith("openai")
                                or k[0].lower().startswith("x-ratelimit"),
                                return_val._nr_response_headers.items(),
                            )
                        )
                        OPENAI_AUDIT_LOG_CONTENTS[prompt][0] = headers
                        OPENAI_AUDIT_LOG_CONTENTS[prompt][2].append(return_val.to_dict_recursive())
                    else:
                        if not getattr(return_val, "data", "").startswith("[DONE]"):
                            OPENAI_AUDIT_LOG_CONTENTS[prompt][2].append(return_val.json())
                return return_val
            except Exception as e:
                raise

        def close(self):
            return super(GeneratorProxy, self).close()

    return GeneratorProxy


@pytest.fixture(scope="session")
def wrap_stream_iter_events(generator_proxy):
    def _wrap_stream_iter_events(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if not transaction:
            return wrapped(*args, **kwargs)

        return_val = wrapped(*args, **kwargs)
        proxied_return_val = generator_proxy(return_val)
        return proxied_return_val

    return _wrap_stream_iter_events
