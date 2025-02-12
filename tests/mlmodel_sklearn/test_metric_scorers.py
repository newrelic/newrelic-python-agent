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
import pytest
from testing_support.fixtures import validate_attributes

from newrelic.api.background_task import background_task
from newrelic.hooks.mlmodel_sklearn import PredictReturnTypeProxy


@pytest.mark.parametrize(
    "metric_scorer_name",
    (
        "accuracy_score",
        "balanced_accuracy_score",
        "f1_score",
        "precision_score",
        "recall_score",
        "roc_auc_score",
        "r2_score",
    ),
)
def test_metric_scorer_attributes(metric_scorer_name, run_metric_scorer):
    @validate_attributes("agent", [f"DecisionTreeClassifier/TrainingStep/0/{metric_scorer_name}"])
    @background_task()
    def _test():
        run_metric_scorer(metric_scorer_name)

    _test()


@pytest.mark.parametrize(
    "metric_scorer_name",
    (
        "accuracy_score",
        "balanced_accuracy_score",
        "f1_score",
        "precision_score",
        "recall_score",
        "roc_auc_score",
        "r2_score",
    ),
)
def test_metric_scorer_training_steps_attributes(metric_scorer_name, run_metric_scorer):
    @validate_attributes(
        "agent",
        [
            f"DecisionTreeClassifier/TrainingStep/0/{metric_scorer_name}",
            f"DecisionTreeClassifier/TrainingStep/1/{metric_scorer_name}",
        ],
    )
    @background_task()
    def _test():
        run_metric_scorer(metric_scorer_name, training_steps=[0, 1])

    _test()


@pytest.mark.parametrize(
    "metric_scorer_name,kwargs",
    [("f1_score", {"average": None}), ("precision_score", {"average": None}), ("recall_score", {"average": None})],
)
def test_metric_scorer_iterable_score_attributes(metric_scorer_name, kwargs, run_metric_scorer):
    @validate_attributes(
        "agent",
        [
            f"DecisionTreeClassifier/TrainingStep/0/{metric_scorer_name}[0]",
            f"DecisionTreeClassifier/TrainingStep/0/{metric_scorer_name}[1]",
        ],
    )
    @background_task()
    def _test():
        run_metric_scorer(metric_scorer_name, kwargs)

    _test()


@pytest.mark.parametrize(
    "metric_scorer_name",
    [
        "accuracy_score",
        "balanced_accuracy_score",
        "f1_score",
        "precision_score",
        "recall_score",
        "roc_auc_score",
        "r2_score",
    ],
)
def test_metric_scorer_attributes_unknown_model(metric_scorer_name):
    @validate_attributes("agent", [f"Unknown/TrainingStep/Unknown/{metric_scorer_name}"])
    @background_task()
    def _test():
        from sklearn import metrics

        y_pred = [1, 0]
        y_test = [1, 0]

        getattr(metrics, metric_scorer_name)(y_test, y_pred)

    _test()


@pytest.mark.parametrize("data", (np.array([0, 1]), "foo", 1, 1.0, True, [0, 1], {"foo": "bar"}, (0, 1), np.str_("F")))
def test_PredictReturnTypeProxy(data):
    wrapped_data = PredictReturnTypeProxy(data, "ModelName", 0)

    assert wrapped_data._nr_model_name == "ModelName"
    assert wrapped_data._nr_training_step == 0


@pytest.fixture
def run_metric_scorer():
    def _run(metric_scorer_name, metric_scorer_kwargs=None, training_steps=None):
        from sklearn import metrics, tree

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[2.0, 2.0], [0, 0.5]]
        y_test = [1, 0]

        if not training_steps:
            training_steps = [0]

        clf = tree.DecisionTreeClassifier(random_state=0)
        for step in training_steps:
            model = clf.fit(x_train, y_train)

            labels = model.predict(x_test)

            metric_scorer_kwargs = metric_scorer_kwargs or {}
            getattr(metrics, metric_scorer_name)(y_test, labels, **metric_scorer_kwargs)

    return _run
