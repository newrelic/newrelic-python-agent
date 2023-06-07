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

import pytest

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_dimensional_metric, record_dimensional_metrics
from newrelic.common.metric_utils import create_metric_identity

from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_dimensional_metrics_outside_transaction import validate_dimensional_metrics_outside_transaction


_test_tags_examples = [
    (None, None),
    ({}, None),
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
def test_record_dimensional_metric_inside_transaction(tags, expected):
    @validate_transaction_metrics("test_record_dimensional_metric_inside_transaction", background_task=True, dimensional_metrics=[
        ("Metric", expected, 1),
    ])
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
def test_record_dimensional_metrics_inside_transaction(tags, expected):
    @validate_transaction_metrics("test_record_dimensional_metrics_inside_transaction", background_task=True, dimensional_metrics=[("Metric/1", expected, 1), ("Metric/2", expected, 1)])
    @background_task(name="test_record_dimensional_metrics_inside_transaction")
    def _test():
        record_dimensional_metrics([("Metric/1", 1, tags), ("Metric/2", 1, tags)])

    _test()


@pytest.mark.parametrize("tags,expected", _test_tags_examples)
@reset_core_stats_engine()
def test_record_dimensional_metrics_outside_transaction(tags, expected):
    @validate_dimensional_metrics_outside_transaction([("Metric/1", expected, 1), ("Metric/2", expected, 1)])
    def _test():
        app = application_instance()
        record_dimensional_metrics([("Metric/1", 1, tags), ("Metric/2", 1, tags)], application=app)

    _test()


def test_dimensional_metrics_different_tags():
    @validate_transaction_metrics("test_dimensional_metrics_different_tags", background_task=True, dimensional_metrics=[
        ("Metric", frozenset({("tag", 1)}), 1),
        ("Metric", frozenset({("tag", 2)}), 2),
    ])
    @background_task(name="test_dimensional_metrics_different_tags")
    def _test():
        record_dimensional_metrics([
            ("Metric", 1, {"tag": 1}),
            ("Metric", 1, {"tag": 2}),
        ])
        record_dimensional_metric("Metric", 1, {"tag": 2})

    _test()
