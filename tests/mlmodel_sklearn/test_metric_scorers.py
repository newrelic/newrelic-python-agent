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
from newrelic.hooks.mlmodel_sklearn import NumpyReturnTypeProxy


def test_metric_scorer_attributes(metric_scorer_name, run_metric_scorer):
    @validate_attributes("agent", ["DecisionTreeClassifier.%s" % metric_scorer_name])
    @background_task()
    def _test():
        run_metric_scorer()

    _test()


def test_metric_scorer_attributes_unknown_model(metric_scorer_name):
    @validate_attributes("agent", ["Unknown.%s" % metric_scorer_name])
    @background_task()
    def _test():
        from sklearn import metrics

        y_pred = [1, 0]
        y_test = [1, 0]

        getattr(metrics, metric_scorer_name)(y_test, y_pred)

    _test()


@pytest.fixture(
    params=[
        "accuracy_score",
        "balanced_accuracy_score",
        "f1_score",
        "precision_score",
        "recall_score",
        "roc_auc_score",
        "r2_score",
    ]
)
def metric_scorer_name(request):
    return request.param


@pytest.mark.parametrize("data", (np.array([0, 1]), "foo", 1, 1.0, True, [0, 1], {"foo": "bar"}, (0, 1), np.str_("F")))
def test_NumpyReturnTypeProxy(data):
    wrapped_data = NumpyReturnTypeProxy(data, "ModelName")

    assert wrapped_data._nr_model_name == "ModelName"


@pytest.fixture
def run_metric_scorer(metric_scorer_name):
    def _run():
        from sklearn import metrics, tree

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[2.0, 2.0], [0, 0.5]]
        y_test = [1, 0]

        clf = tree.DecisionTreeClassifier(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return getattr(metrics, metric_scorer_name)(y_test, labels)

    return _run
