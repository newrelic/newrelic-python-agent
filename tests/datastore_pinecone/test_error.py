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

import pinecone
import pytest
from testing_support.fixtures import callable_name
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task


@pytest.fixture(scope="function")
def pinecone_instance2(pinecone_client):
    # Delete if already exists/did not get properly deleted
    # from previous runs
    if "python-test" in pinecone_client.list_indexes().names():
        pinecone_client.delete_index("python-test")

    pinecone_client.create_index(
        name="python-test",
        dimension=4,
        metric="cosine",
        spec=pinecone.PodSpec(
            environment="us-east-1-aws",
            pod_type="p1.x2",
            pods=1,
        ),
    )

    yield pinecone_client
    pinecone_client.delete_index("python-test")


@validate_error_trace_attributes(
    callable_name(pinecone.PineconeApiTypeError),
)
@validate_span_events(
    exact_agents={
        "error.message": "Invalid type for variable 'replicas'. Required value type is int and passed type was float at ['replicas']",
    }
)
@background_task()
def test_api_type_error(pinecone_instance):
    with pytest.raises(pinecone.PineconeApiTypeError):
        pinecone_instance.configure_index("python-test", 5.2, pod_type="p1.x2")


@validate_error_trace_attributes(
    callable_name(pinecone.PineconeApiValueError),
)
@validate_span_events(
    exact_agents={
        "error.message": "Invalid value for `metric` (invalid), must be one of ['cosine', 'euclidean', 'dotproduct']",
    }
)
@background_task()
def test_api_value_error(pinecone_client):
    with pytest.raises(pinecone.PineconeApiValueError):
        pinecone_client.create_index(
            name="failure-index",
            dimension=4,
            metric="invalid",
            spec=pinecone.PodSpec(
                environment="us-east-1-aws",
                pod_type="p1.x1",
                pods=1,
            ),
        )


@validate_error_trace_attributes(
    callable_name(pinecone.NotFoundException),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 404,
            "error.code": "NOT_FOUND",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Resource failure-index not found",
    }
)
@background_task()
def test_not_found_exception(pinecone_client):
    with pytest.raises(pinecone.NotFoundException):
        pinecone_client.delete_index("failure-index")


@validate_error_trace_attributes(
    callable_name(pinecone.UnauthorizedException),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
            "error.code": "Unauthorized",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Invalid API Key",
    },
)
@background_task()
def test_unauthorized_exception():
    with pytest.raises(pinecone.UnauthorizedException):
        pinecone_client = pinecone.Pinecone(api_key="NOT-A-VALID-API-KEY")
        pinecone_client.create_index(
            name="invalid-api-index",
            dimension=4,
            metric="cosine",
            spec=pinecone.PodSpec(
                environment="us-east-1-aws",
                pod_type="p1.x1",
                pods=1,
            ),
        )


@validate_error_trace_attributes(
    callable_name(pinecone.PineconeApiException),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 400,
            "error.code": "INVALID_ARGUMENT",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Bad request: Cannot scale down an index, only up. Current size is: 1",
    }
)
@background_task()
def test_api_exception(pinecone_instance2):
    with pytest.raises(pinecone.PineconeApiException):
        pinecone_instance2.configure_index("python-test", pod_type="p1.x1")


# PineconeApiAttributeError is not accessed
# PineconeApiKeyError not actually used
# ForbiddenException the result of exceeding pod/collection
#   quota or having a free tier API key while trying to use
#   indexing commands that are only available to the paid tier
#   (e.g. collections related commands)
# ServiceException is a server related error
