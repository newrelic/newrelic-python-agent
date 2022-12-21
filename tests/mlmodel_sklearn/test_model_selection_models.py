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
from sklearn.ensemble import AdaBoostClassifier

# from sklearn.model_selection import RandomForestClassifier, RandomForestRegressor
# from sklearn.linear_model import LinearRegression
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version
from newrelic.packages import six

SKLEARN_VERSION = tuple(map(int, get_package_version("sklearn").split(".")))


@pytest.mark.parametrize(
    "model_selection_model_name",
    [
        "GridSearchCV",
        "RandomizedSearchCV",
    ],
)
def test_model_methods_wrapped_in_function_trace(model_selection_model_name, run_model_selection_model):
    expected_scoped_metrics = {
        "GridSearchCV": [
            ("Function/MLModel/Sklearn/Named/GridSearchCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/GridSearchCV.predict", 1),
            ("Function/MLModel/Sklearn/Named/GridSearchCV.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/GridSearchCV.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/GridSearchCV.score", 1),
            # ("Function/MLModel/Sklearn/Named/GridSearchCV.transform", 1),
        ],
        "RandomizedSearchCV": [
            ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.predict", 1),
            ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.score", 1),
            # ("Function/MLModel/Sklearn/Named/RandomizedSearchCV.transform", 1),
        ],
    }

    expected_transaction_name = (
        "test_model_selection_models:test_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_model_selection_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[model_selection_model_name],
        rollup_metrics=expected_scoped_metrics[model_selection_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_model_selection_model(model_selection_model_name)

    _test()


# @pytest.mark.skipif(SKLEARN_VERSION < (1, 0, 0) or SKLEARN_VERSION >= (1, 1, 0), reason="Requires 1.0 <= sklearn < 1.1")
# @pytest.mark.parametrize(
#     "model_selection_model_name",
#     [
#         "HistGradientBoostingClassifier",
#         "HistGradientBoostingRegressor",
#         "StackingClassifier",
#         "StackingRegressor",
#         "VotingRegressor",
#     ],
# )
# def test_between_v1_0_and_v1_1_model_methods_wrapped_in_function_trace(
#     model_selection_model_name, run_model_selection_model
# ):
#     expected_scoped_metrics = {
#         "HistGradientBoostingClassifier": [
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.fit", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 2),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.score", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 3),
#         ],
#         "HistGradientBoostingRegressor": [
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.fit", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.predict", 2),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.score", 1),
#         ],
#         "StackingClassifier": [
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.fit", 1),
#         ],
#         "StackingRegressor": [
#             ("Function/MLModel/Sklearn/Named/StackingRegressor.fit", 1),
#         ],
#         "VotingRegressor": [
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.fit", 1),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.predict", 2),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.score", 1),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.transform", 1),
#         ],
#     }
#     expected_transaction_name = (
#         "test_model_selection_models:test_between_v1_0_and_v1_1_model_methods_wrapped_in_function_trace.<locals>._test"
#         if six.PY3
#         else "test_model_selection_models:_test"
#     )

#     @validate_transaction_metrics(
#         expected_transaction_name,
#         scoped_metrics=expected_scoped_metrics[model_selection_model_name],
#         rollup_metrics=expected_scoped_metrics[model_selection_model_name],
#         background_task=True,
#     )
#     @background_task()
#     def _test():
#         run_model_selection_model(model_selection_model_name)

#     _test()


# @pytest.mark.skipif(SKLEARN_VERSION < (1, 1, 0), reason="Requires sklearn >= 1.1")
# @pytest.mark.parametrize(
#     "model_selection_model_name",
#     [
#         "HistGradientBoostingClassifier",
#         "HistGradientBoostingRegressor",
#         "StackingClassifier",
#         "StackingRegressor",
#         "VotingRegressor",
#     ],
# )
# def test_above_v1_1_model_methods_wrapped_in_function_trace(model_selection_model_name, run_model_selection_model):
#     expected_scoped_metrics = {
#         "StackingClassifier": [
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.fit", 1),
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.predict", 2),
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.score", 1),
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.predict_proba", 1),
#             ("Function/MLModel/Sklearn/Named/StackingClassifier.transform", 4),
#         ],
#         "StackingRegressor": [
#             ("Function/MLModel/Sklearn/Named/StackingRegressor.fit", 1),
#             ("Function/MLModel/Sklearn/Named/StackingRegressor.predict", 2),
#             ("Function/MLModel/Sklearn/Named/StackingRegressor.score", 1),
#         ],
#         "VotingRegressor": [
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.fit", 1),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.predict", 2),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.score", 1),
#             ("Function/MLModel/Sklearn/Named/VotingRegressor.transform", 1),
#         ],
#         "HistGradientBoostingClassifier": [
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.fit", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 2),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.score", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 3),
#         ],
#         "HistGradientBoostingRegressor": [
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.fit", 1),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.predict", 2),
#             ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.score", 1),
#         ],
#     }
#     expected_transaction_name = (
#         "test_model_selection_models:test_above_v1_1_model_methods_wrapped_in_function_trace.<locals>._test"
#         if six.PY3
#         else "test_model_selection_models:_test"
#     )

#     @validate_transaction_metrics(
#         expected_transaction_name,
#         scoped_metrics=expected_scoped_metrics[model_selection_model_name],
#         rollup_metrics=expected_scoped_metrics[model_selection_model_name],
#         background_task=True,
#     )
#     @background_task()
#     def _test():
#         run_model_selection_model(model_selection_model_name)

#     _test()


@pytest.fixture
def run_model_selection_model():
    def _run(model_selection_model_name):
        import sklearn.model_selection
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        parameters = {"kernel": ("linear", "rbf"), "C": [1, 10]}
        kwargs = {"estimator": AdaBoostClassifier(), "param_grid": parameters}
        # if ensemble_model_name == "StackingClassifier":
        #     kwargs = {"estimators": [("rf", RandomForestClassifier())], "final_estimator": RandomForestClassifier()}
        # elif ensemble_model_name == "VotingClassifier":
        #     kwargs = {
        #         "estimators": [("rf", RandomForestClassifier())],
        #         "voting": "soft",
        #     }
        # elif ensemble_model_name == "VotingRegressor":
        #     kwargs = {"estimators": [("lr", LinearRegression())]}
        # elif ensemble_model_name == "StackingRegressor":
        #     kwargs = {"estimators": [("rf", RandomForestRegressor())]}
        clf = getattr(sklearn.model_selection, model_selection_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
