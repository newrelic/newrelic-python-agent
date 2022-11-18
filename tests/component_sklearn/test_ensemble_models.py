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
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.packages import six


def test_model_methods_wrapped_in_function_trace(ensemble_model_name, run_ensemble_model):
    expected_scoped_metrics = {
        "AdaBoostClassifier": [
            ("MLModel/Sklearn/Named/AdaBoostClassifier.predict", 1),
            ("MLModel/Sklearn/Named/AdaBoostClassifier.predict_log_proba", 1),
            ("MLModel/Sklearn/Named/AdaBoostClassifier.predict_proba", 1),
            ("MLModel/Sklearn/Named/AdaBoostClassifier.staged_predict", 1),
            ("MLModel/Sklearn/Named/AdaBoostClassifier.staged_predict_proba", 1),
        ],
        "AdaBoostRegressor": [
            ("MLModel/Sklearn/Named/AdaBoostRegressor.predict", 1),
            ("MLModel/Sklearn/Named/AdaBoostRegressor.staged_predict", 1),
        ],
        "BaggingClassifier": [
            ("MLModel/Sklearn/Named/BaggingClassifier.predict", 1),
            ("MLModel/Sklearn/Named/BaggingClassifier.predict_log_proba", 1),
            ("MLModel/Sklearn/Named/BaggingClassifier.predict_proba", 1),
        ],
        "BaggingRegressor": [
            ("MLModel/Sklearn/Named/BaggingRegressor.predict", 1),
        ],
        "ExtraTreesClassifier": [
            ("MLModel/Sklearn/Named/ExtraTreesClassifier.predict", 1),
            ("MLModel/Sklearn/Named/ExtraTreesClassifier.predict_log_proba", 1),
            ("MLModel/Sklearn/Named/ExtraTreesClassifier.predict_proba", 1),
        ],
        "ExtraTreesRegressor": [
            ("MLModel/Sklearn/Named/ExtraTreesRegressor.predict", 1),
        ],
        "GradientBoostingClassifier": [
            ("MLModel/Sklearn/Named/GradientBoostingClassifier.predict", 1),
            ("MLModel/Sklearn/Named/GradientBoostingClassifier.predict_log_proba", 1),
            ("MLModel/Sklearn/Named/GradientBoostingClassifier.predict_proba", 1),
            ("MLModel/Sklearn/Named/GradientBoostingClassifier.staged_predict", 1),
            ("MLModel/Sklearn/Named/GradientBoostingClassifier.staged_predict_proba", 1),
        ],
        "GradientBoostingRegressor": [
            ("MLModel/Sklearn/Named/GradientBoostingRegressor.predict", 1),
            ("MLModel/Sklearn/Named/GradientBoostingRegressor.staged_predict", 1),
        ],
        "HistGradientBoostingClassifier": [
            ("MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 1),
            ("MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 1),
            ("MLModel/Sklearn/Named/HistGradientBoostingClassifier.staged_predict", 1),
            ("MLModel/Sklearn/Named/HistGradientBoostingClassifier.staged_predict_proba", 1),
        ],
        "HistGradientBoostingRegressor": [
            ("MLModel/Sklearn/Named/HistGradientBoostingRegressor.predict", 1),
            ("MLModel/Sklearn/Named/HistGradientBoostingRegressor.staged_predict", 1),
        ],
        "IsolationForest": [
            ("MLModel/Sklearn/Named/IsolationForest.fit_predict", 1),
            ("MLModel/Sklearn/Named/IsolationForest.predict", 1),
        ],
        "RandomForestClassifier": [
            ("MLModel/Sklearn/Named/RandomForestClassifier.predict", 1),
            ("MLModel/Sklearn/Named/RandomForestClassifier.predict_log_proba", 1),
            ("MLModel/Sklearn/Named/RandomForestClassifier.predict_proba", 1),
        ],
        "RandomForestRegressor": [
            ("MLModel/Sklearn/Named/RandomForestRegressor.predict", 1),
        ],
        "StackingClassifier": [
            ("MLModel/Sklearn/Named/StackingClassifier.predict", 1),
            ("MLModel/Sklearn/Named/StackingClassifier.predict_proba", 1),
        ],
        "StackingRegressor": [
            ("MLModel/Sklearn/Named/StackingRegressor.predict", 1),
        ],
        "VotingClassifier": [
            ("MLModel/Sklearn/Named/VotingClassifier.predict", 1),
            ("MLModel/Sklearn/Named/VotingClassifier.predict_proba", 1),
        ],
        "VotingRegressor": [
            ("MLModel/Sklearn/Named/VotingRegressor.predict", 1),
        ],
    }
    expected_transaction_name = "test_ensemble_models:_test"
    if six.PY3:
        expected_transaction_name = "test_ensemble_models:test_model_methods_wrapped_in_function_trace.<locals>._test"

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[ensemble_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_ensemble_model()

    _test()


@pytest.fixture(
    params=[
        "AdaBoostClassifier",
        "AdaBoostRegressor",
        "BaggingClassifier",
        "BaggingRegressor",
        "ExtraTreesClassifier",
        "ExtraTreesRegressor",
        "GradientBoostingClassifier",
        "GradientBoostingRegressor",
        "HistGradientBoostingClassifier",
        "HistGradientBoostingRegressor",
        "IsolationForest",
        "RandomForestClassifier",
        "StackingClassifier",
        "VotingClassifier",
        "VotingRegressor",
    ]
)
def ensemble_model_name(request):
    return request.param


@pytest.fixture
def run_ensemble_model(ensemble_model_name):
    def _run():
        import sklearn

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[2.0, 2.0], [2.0, 1.0]]
        # y_test = [1, 1]

        clf = getattr(sklearn.ensemble, ensemble_model_name)(random_state=0)
        model = clf.fit(x_train, y_train)

        model.staged_predict(x_train)
        model.staged_predict_proba(x_train)
        model.predict(x_test)

        # Only classifier models have proba methods.
        classifier_models = (
            "AdaBoostClassifier",
            "BaggingClassifier",
            "ExtraTreesClassifier",
            "GradientBoostingClassifier",
            "HistGradientBoostingClassifier",
            "RandomForestClassifier",
            "StackingClassifier",
            "VotingClassifier",
        )
        if ensemble_model_name in classifier_models:
            model.predict_log_proba(x_test)
            model.predict_proba(x_test)

    return _run
