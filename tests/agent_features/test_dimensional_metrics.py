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

from importlib import reload

import pytest
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_dimensional_metric_payload import validate_dimensional_metric_payload
from testing_support.validators.validate_dimensional_metrics_outside_transaction import (
    validate_dimensional_metrics_outside_transaction,
)
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

import newrelic.core.otlp_utils
from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_dimensional_metric, record_dimensional_metrics
from newrelic.common.metric_utils import create_metric_identity
from newrelic.core.config import global_settings


@pytest.fixture(scope="module", autouse=True, params=["protobuf", "json"])
def otlp_content_encoding(request):
    _settings = global_settings()
    prev = _settings.debug.otlp_content_encoding
    _settings.debug.otlp_content_encoding = request.param
    reload(newrelic.core.otlp_utils)
    assert newrelic.core.otlp_utils.otlp_content_setting == request.param, "Content encoding mismatch."

    yield

    _settings.debug.otlp_content_encoding = prev


_test_tags_examples = [
    (None, None),
    ({}, None),
    ({"drop-me": None}, None),
    ([], None),
    ({"str": "a"}, frozenset({("str", "a")})),
    ({"int": 1}, frozenset({("int", 1)})),
    ({"float": 1.0}, frozenset({("float", 1.0)})),
    ({"bool": True}, frozenset({("bool", True)})),
    ({"list": [1]}, frozenset({("list", "[1]")})),
    ({"dict": {"subtag": 1}}, frozenset({("dict", "{'subtag': 1}")})),
    ([("tags-as-list", 1)], frozenset({("tags-as-list", 1)})),
]


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
def test_create_metric_identity(tags, expected):
    name = "Metric"
    output_name, output_tags = create_metric_identity(name, tags=tags)
    assert output_name == name, "Name does not match."
    assert output_tags == expected, "Output tags do not match."


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
@reset_core_stats_engine()
def test_record_dimensional_metric_inside_transaction(tags, expected):
    @validate_transaction_metrics(
        "test_record_dimensional_metric_inside_transaction",
        background_task=True,
        dimensional_metrics=[("Metric", expected, 1)],
    )
    @background_task(name="test_record_dimensional_metric_inside_transaction")
    def _test():
        record_dimensional_metric("Metric", 1, tags=tags)

    _test()


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
@reset_core_stats_engine()
def test_record_dimensional_metric_outside_transaction(tags, expected):
    @validate_dimensional_metrics_outside_transaction([("Metric", expected, 1)])
    def _test():
        app = application_instance()
        record_dimensional_metric("Metric", 1, tags=tags, application=app)

    _test()


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
@reset_core_stats_engine()
def test_record_dimensional_metrics_inside_transaction(tags, expected):
    @validate_transaction_metrics(
        "test_record_dimensional_metrics_inside_transaction",
        background_task=True,
        dimensional_metrics=[("Metric.1", expected, 1), ("Metric.2", expected, 1)],
    )
    @background_task(name="test_record_dimensional_metrics_inside_transaction")
    def _test():
        record_dimensional_metrics([("Metric.1", 1, tags), ("Metric.2", 1, tags)])

    _test()


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
@reset_core_stats_engine()
def test_record_dimensional_metrics_outside_transaction(tags, expected):
    @validate_dimensional_metrics_outside_transaction([("Metric.1", expected, 1), ("Metric.2", expected, 1)])
    def _test():
        app = application_instance()
        record_dimensional_metrics([("Metric.1", 1, tags), ("Metric.2", 1, tags)], application=app)

    _test()


@reset_core_stats_engine()
def test_dimensional_metrics_different_tags():
    @validate_transaction_metrics(
        "test_dimensional_metrics_different_tags",
        background_task=True,
        dimensional_metrics=[("Metric", frozenset({("tag", 1)}), 1), ("Metric", frozenset({("tag", 2)}), 2)],
    )
    @background_task(name="test_dimensional_metrics_different_tags")
    def _test():
        record_dimensional_metrics([("Metric", 1, {"tag": 1}), ("Metric", 1, {"tag": 2})])
        record_dimensional_metric("Metric", 1, {"tag": 2})

    _test()


@reset_core_stats_engine()
@validate_dimensional_metric_payload(
    summary_metrics=[
        ("Metric.Summary", {"tag": 1}, 1),
        ("Metric.Summary", {"tag": 2}, 1),
        ("Metric.Summary", None, 1),
        ("Metric.Mixed", {"tag": 1}, 1),
        ("Metric.NotPresent", None, None),
    ],
    count_metrics=[
        ("Metric.Count", {"tag": 1}, 1),
        ("Metric.Count", {"tag": 2}, 2),
        ("Metric.Count", None, 3),
        ("Metric.Mixed", {"tag": 2}, 2),
        ("Metric.NotPresent", None, None),
    ],
)
def test_dimensional_metrics_payload():
    @background_task(name="test_dimensional_metric_payload")
    def _test():
        record_dimensional_metrics(
            [
                ("Metric.Summary", 1, {"tag": 1}),
                ("Metric.Summary", 2, {"tag": 2}),
                ("Metric.Summary", 3),  # No tags
                ("Metric.Count", {"count": 1}, {"tag": 1}),
                ("Metric.Count", {"count": 2}, {"tag": 2}),
                ("Metric.Count", {"count": 3}),  # No tags
                ("Metric.Mixed", 1, {"tag": 1}),
                ("Metric.Mixed", {"count": 2}, {"tag": 2}),
            ]
        )

    _test()
    app = application_instance()
    core_app = app._agent.application(app.name)
    core_app.harvest()


@reset_core_stats_engine()
@validate_dimensional_metric_payload(
    summary_metrics=[
        ("Metric.Summary", None, 1),
        ("Metric.Count", None, None),  # Should NOT be present
    ],
    count_metrics=[
        ("Metric.Count", None, 1),
        ("Metric.Summary", None, None),  # Should NOT be present
    ],
)
def test_dimensional_metrics_no_duplicate_encodings():
    @background_task(name="test_dimensional_metric_payload")
    def _test():
        record_dimensional_metrics([("Metric.Summary", 1), ("Metric.Count", {"count": 1})])

    _test()
    app = application_instance()
    core_app = app._agent.application(app.name)
    core_app.harvest()
