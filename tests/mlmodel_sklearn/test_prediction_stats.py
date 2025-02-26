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

import uuid

import numpy as np
import pandas as pd
import pytest
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# This will act as the UUID for `prediction_id`
ML_METRIC_FORCED_UUID = "0b59992f-2349-4a46-8de1-696d3fe1088b"


@pytest.fixture(scope="function")
def force_uuid(monkeypatch):
    monkeypatch.setattr(uuid, "uuid4", lambda *a, **k: ML_METRIC_FORCED_UUID)


_test_prediction_stats_tags = frozenset(
    {("modelName", "DummyClassifier"), ("prediction_id", ML_METRIC_FORCED_UUID), ("model_version", "0.0.0")}
)


@pytest.mark.parametrize(
    "x_train,y_train,x_test,metrics",
    [
        (
            [[0, 0], [1, 1]],
            [0, 1],
            [[2.0, 2.0], [0, 0.5]],
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
        (
            np.array([[0, 0], [1, 1]]),
            [0, 1],
            np.array([[2.0, 2.0], [0, 0.5]]),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
        (
            np.array([["a", 0, 4], ["b", 1, 3]], dtype="<U4"),
            [0, 1],
            np.array([["a", 2.0, 3], ["b", 0.5, 4]], dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", _test_prediction_stats_tags, None),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    None,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
        (
            pd.DataFrame({"col1": [0, 0], "col2": [1, 1]}),
            [0, 1],
            pd.DataFrame({"col1": [2.0, 2.0], "col2": [0, 0.5]}),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
        (
            pd.DataFrame({"col1": ["a", "b"], "col2": [0.5, 1]}, dtype="<U4"),
            [0, 1],
            pd.DataFrame({"col1": ["a", "b"], "col2": [0, 0.5]}, dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", _test_prediction_stats_tags, None),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation",
                    _test_prediction_stats_tags,
                    None,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75",
                    _test_prediction_stats_tags,
                    1,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
        (
            pd.DataFrame({"col1": ["a", "b"], "col2": [True, False]}, dtype="<U4"),
            [0, 1],
            pd.DataFrame({"col1": ["a", "c"], "col2": [True, False]}, dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", _test_prediction_stats_tags, None),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation",
                    _test_prediction_stats_tags,
                    None,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", _test_prediction_stats_tags, None),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75",
                    _test_prediction_stats_tags,
                    None,
                ),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation",
                    _test_prediction_stats_tags,
                    None,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", _test_prediction_stats_tags, None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", _test_prediction_stats_tags, 1),
                (
                    "MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation",
                    _test_prediction_stats_tags,
                    1,
                ),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", _test_prediction_stats_tags, 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", _test_prediction_stats_tags, 1),
            ],
        ),
    ],
)
def test_prediction_stats(run_model, x_train, y_train, x_test, metrics, force_uuid):
    expected_transaction_name = "test_prediction_stats:test_prediction_stats.<locals>._test"

    @validate_transaction_metrics(expected_transaction_name, dimensional_metrics=metrics, background_task=True)
    @background_task()
    def _test():
        run_model(x_train, y_train, x_test)

    _test()


_test_prediction_stats_multilabel_output_tags = frozenset(
    {("modelName", "MultiOutputClassifier"), ("prediction_id", ML_METRIC_FORCED_UUID), ("model_version", "0.0.0")}
)


def test_prediction_stats_multilabel_output(force_uuid):
    expected_transaction_name = "test_prediction_stats:test_prediction_stats_multilabel_output.<locals>._test"
    stats = ["Mean", "Percentile25", "Percentile50", "Percentile75", "StandardDeviation", "Min", "Max", "Count"]
    metrics = [
        (
            f"MLModel/Sklearn/Named/MultiOutputClassifier/Predict/Feature/{feature_col}/{stat_name}",
            _test_prediction_stats_multilabel_output_tags,
            1,
        )
        for feature_col in range(20)
        for stat_name in stats
    ]
    metrics.extend(
        [
            (
                f"MLModel/Sklearn/Named/MultiOutputClassifier/Predict/Label/{label_col}/{stat_name}",
                _test_prediction_stats_multilabel_output_tags,
                1,
            )
            for label_col in range(3)
            for stat_name in stats
        ]
    )

    @validate_transaction_metrics(expected_transaction_name, dimensional_metrics=metrics, background_task=True)
    @background_task()
    def _test():
        from sklearn.datasets import make_multilabel_classification
        from sklearn.linear_model import LogisticRegression
        from sklearn.multioutput import MultiOutputClassifier

        x_train, y_train = make_multilabel_classification(n_classes=3, random_state=0)
        clf = MultiOutputClassifier(LogisticRegression()).fit(x_train, y_train)
        clf.predict([x_train[-1]])

    _test()


@pytest.fixture
def run_model():
    def _run(x_train, y_train, x_test):
        from sklearn import dummy

        clf = dummy.DummyClassifier(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)

    return _run
