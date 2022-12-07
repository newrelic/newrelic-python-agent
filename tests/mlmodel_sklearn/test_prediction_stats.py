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

import numpy as np
import pandas as pd
import pytest
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.packages import six


@pytest.mark.parametrize(
    "x_train,y_train,x_test,metrics",
    [
        (
            [[0, 0], [1, 1]],
            [0, 1],
            [[2.0, 2.0], [0, 0.5]],
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
        (
            np.array([[0, 0], [1, 1]]),
            [0, 1],
            np.array([[2.0, 2.0], [0, 0.5]]),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
        (
            np.array([["a", 0, 4], ["b", 1, 3]], dtype="<U4"),
            [0, 1],
            np.array([["a", 2.0, 3], ["b", 0.5, 4]], dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Mean", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile25", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile50", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Percentile75", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/StandardDeviation", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Min", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Max", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/0/Count", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/1/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
        (
            pd.DataFrame({"col1": [0, 0], "col2": [1, 1]}),
            [0, 1],
            pd.DataFrame({"col1": [2.0, 2.0], "col2": [0, 0.5]}),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
        (
            pd.DataFrame({"col1": ["a", "b"], "col2": [0.5, 1]}, dtype="<U4"),
            [0, 1],
            pd.DataFrame({"col1": ["a", "b"], "col2": [0, 0.5]}, dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
        (
            pd.DataFrame({"col1": ["a", "b"], "col2": [True, False]}, dtype="<U4"),
            [0, 1],
            pd.DataFrame({"col1": ["a", "c"], "col2": [True, False]}, dtype="<U4"),
            [
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Mean", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile25", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile50", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Percentile75", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/StandardDeviation", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Min", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Max", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col1/Count", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Mean", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile25", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile50", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Percentile75", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/StandardDeviation", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Min", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Max", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Feature/col2/Count", None),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Mean", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile25", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile50", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Percentile75", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/StandardDeviation", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Min", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Max", 1),
                ("MLModel/Sklearn/Named/DummyClassifier/Predict/Label/0/Count", 1),
            ],
        ),
    ],
)
def test_prediction_stats(run_model, x_train, y_train, x_test, metrics):
    expected_transaction_name = (
        "test_prediction_stats:test_prediction_stats.<locals>._test" if six.PY3 else "test_prediction_stats:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        custom_metrics=metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        run_model(x_train, y_train, x_test)

    _test()


def test_prediction_stats_multilabel_output():
    expected_transaction_name = (
        "test_prediction_stats:test_prediction_stats_multilabel_output.<locals>._test"
        if six.PY3
        else "test_prediction_stats:_test"
    )
    stats = ["Mean", "Percentile25", "Percentile50", "Percentile75", "StandardDeviation", "Min", "Max", "Count"]
    metrics = [
        ("MLModel/Sklearn/Named/MultiOutputClassifier/Predict/Feature/%s/%s" % (feature_col, stat_name), 1)
        for feature_col in range(20)
        for stat_name in stats
    ]
    metrics.extend(
        [
            ("MLModel/Sklearn/Named/MultiOutputClassifier/Predict/Label/%s/%s" % (label_col, stat_name), 1)
            for label_col in range(3)
            for stat_name in stats
        ]
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        custom_metrics=metrics,
        background_task=True,
    )
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
