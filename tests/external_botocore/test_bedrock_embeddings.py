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

import copy
import json
from io import BytesIO

import pytest
from testing_support.fixtures import (  # override_application_settings,
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

from _test_bedrock_embeddings import embedding_expected_events, embedding_payload_templates

disabled_ml_insights_settings = {"ml_insights_events.enabled": False}


@pytest.fixture(scope="session", params=[False, True], ids=["Bytes", "Stream"])
def is_file_payload(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=[
        "amazon.titan-embed-text-v1",
        "amazon.titan-embed-g1-text-02",
    ],
)
def model_id(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, is_file_payload):
    payload_template = embedding_payload_templates[model_id]

    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % prompt).encode("utf-8")
        if is_file_payload:
            body = BytesIO(body)

        response = bedrock_server.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response.get("body").read())
        assert response_body

    return _exercise_model


@pytest.fixture(scope="module")
def expected_events(model_id):
    return embedding_expected_events[model_id]


@reset_core_stats_engine()
def test_bedrock_embedding(set_trace_info, exercise_model, expected_events):
    @validate_ml_events(expected_events)
    @validate_ml_event_count(count=1)
    # @validate_transaction_metrics(
    #     name="test_bedrock_embedding",
    #     custom_metrics=[
    #         ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    #     ],
    #     background_task=True,
    # )
    @background_task(name="test_bedrock_embedding")
    def _test():
        set_trace_info()
        exercise_model(prompt="This is an embedding test.")

    _test()


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_bedrock_embedding_outside_txn(exercise_model):
    exercise_model(prompt="This is an embedding test.")


@override_application_settings(disabled_ml_insights_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
# @validate_transaction_metrics(
#     name="test_embeddings:test_bedrock_embedding_disabled_settings",
#     custom_metrics=[
#         ("Python/ML/OpenAI/%s" % openai.__version__, 1),
#     ],
#     background_task=True,
# )
@background_task()
def test_bedrock_embedding_disabled_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt="This is an embedding test.")
