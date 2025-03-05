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
    "ml_insights_events.enabled": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_openai)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_openai)"],
)

if get_openai_version() < (1, 0):
    collect_ignore = [
        "test_chat_completion_v1.py",
        "test_chat_completion_error_v1.py",
        "test_embeddings_v1.py",
        "test_embeddings_error_v1.py",
        "test_chat_completion_stream_v1.py",
        "test_chat_completion_stream_error_v1.py",
        "test_embeddings_stream_v1.py",
    ]
else:
    collect_ignore = [
        "test_embeddings.py",
        "test_embeddings_error.py",
        "test_chat_completion.py",
        "test_chat_completion_error.py",
        "test_chat_completion_stream.py",
        "test_chat_completion_stream_error.py",
    ]


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
    import openai

    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        with MockExternalOpenAIServer() as server:
            if openai_version < (1, 0):
                openai.api_base = f"http://localhost:{server.port}"
                openai.api_key = "NOT-A-REAL-SECRET"
                yield
            else:
                openai_sync = openai.OpenAI(base_url=f"http://localhost:{server.port}", api_key="NOT-A-REAL-SECRET")
                openai_async = openai.AsyncOpenAI(
                    base_url=f"http://localhost:{server.port}", api_key="NOT-A-REAL-SECRET"
                )
                yield (openai_sync, openai_async)
    else:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")

        if openai_version < (1, 0):
            openai.api_key = openai_api_key
            yield
        else:
            openai_sync = openai.OpenAI(api_key=openai_api_key)
            openai_async = openai.AsyncOpenAI(api_key=openai_api_key)
            yield (openai_sync, openai_async)


@pytest.fixture(scope="session")
def sync_openai_client(openai_clients):
    sync_client, _ = openai_clients
    return sync_client


@pytest.fixture(scope="session")
def async_openai_client(openai_clients):
    _, async_client = openai_clients
    return async_client


@pytest.fixture(autouse=True, scope="session")
def openai_server(
    openai_version,  # noqa: F811
    openai_clients,
    wrap_openai_api_requestor_request,
    wrap_openai_api_requestor_interpret_response,
    wrap_httpx_client_send,
    wrap_engine_api_resource_create,
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
        if openai_version < (1, 0):
            # Apply function wrappers to record data
            wrap_function_wrapper("openai.api_requestor", "APIRequestor.request", wrap_openai_api_requestor_request)
            wrap_function_wrapper(
                "openai.api_requestor", "APIRequestor._interpret_response", wrap_openai_api_requestor_interpret_response
            )
            wrap_function_wrapper(
                "openai.api_resources.abstract.engine_api_resource",
                "EngineAPIResource.create",
                wrap_engine_api_resource_create,
            )
            yield  # Run tests
        else:
            # Apply function wrappers to record data
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

        if response.status_code >= 500 or response.status_code < 200:
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
        if stream:
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = [headers, response.status_code, []]  # Append response data to log
            if prompt == "error":
                OPENAI_AUDIT_LOG_CONTENTS[prompt][2] = json.loads(response.read())
        else:
            body = json.loads(response.content.decode("utf-8"))
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = headers, response.status_code, body  # Append response data to log
        return response

    return _wrap_httpx_client_send


@pytest.fixture(scope="session")
def wrap_openai_api_requestor_interpret_response():
    def _wrap_openai_api_requestor_interpret_response(wrapped, instance, args, kwargs):
        rbody, rcode, rheaders = bind_request_interpret_response_params(*args, **kwargs)
        headers = dict(
            filter(
                lambda k: k[0].lower() in RECORDED_HEADERS
                or k[0].lower().startswith("openai")
                or k[0].lower().startswith("x-ratelimit"),
                rheaders.items(),
            )
        )

        if rcode >= 400 or rcode < 200:
            rbody = json.loads(rbody)
            OPENAI_AUDIT_LOG_CONTENTS["error"] = headers, rcode, rbody  # Append response data to audit log
        return wrapped(*args, **kwargs)

    return _wrap_openai_api_requestor_interpret_response


@pytest.fixture(scope="session")
def wrap_openai_api_requestor_request(extract_shortened_prompt):  # noqa: F811
    def _wrap_openai_api_requestor_request(wrapped, instance, args, kwargs):
        params = bind_request_params(*args, **kwargs)
        if not params:
            return wrapped(*args, **kwargs)

        prompt = extract_shortened_prompt(params)

        # Send request
        result = wrapped(*args, **kwargs)

        # Append response data to audit log
        if not kwargs.get("stream", False):
            # Clean up data
            data = result[0].data
            headers = result[0]._headers
            headers = dict(
                filter(
                    lambda k: k[0].lower() in RECORDED_HEADERS
                    or k[0].lower().startswith("openai")
                    or k[0].lower().startswith("x-ratelimit"),
                    headers.items(),
                )
            )
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = headers, 200, data
        else:
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = [None, 200, []]
        return result

    return _wrap_openai_api_requestor_request


def bind_request_params(method, url, params=None, *args, **kwargs):
    return params


def bind_request_interpret_response_params(result, stream):
    return result.content.decode("utf-8"), result.status_code, result.headers


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
def wrap_engine_api_resource_create(generator_proxy):
    def _wrap_engine_api_resource_create(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if not transaction:
            return wrapped(*args, **kwargs)

        bound_args = bind_args(wrapped, args, kwargs)
        stream = bound_args["params"].get("stream", False)

        return_val = wrapped(*args, **kwargs)

        if stream:
            return generator_proxy(return_val)
        else:
            return return_val

    return _wrap_engine_api_resource_create


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
