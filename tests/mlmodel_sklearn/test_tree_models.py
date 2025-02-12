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
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


def test_model_methods_wrapped_in_function_trace(tree_model_name, run_tree_model):
    # Note: in the following expected metrics, predict and predict_proba are called by
    # score and predict_log_proba so they are expected to be called twice instead of
    # once like the rest of the methods.
    expected_scoped_metrics = {
        "ExtraTreeRegressor": [
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.score", 1),
        ],
        "DecisionTreeClassifier": [
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict_proba", 2),
        ],
        "ExtraTreeClassifier": [
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict_proba", 2),
        ],
        "DecisionTreeRegressor": [
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.score", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_tree_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[tree_model_name],
        rollup_metrics=expected_scoped_metrics[tree_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_tree_model()

    _test()


def test_multiple_calls_to_model_methods(tree_model_name, run_tree_model):
    # Note: in the following expected metrics, predict and predict_proba are called by
    # score and predict_log_proba so they are expected to be called twice as often as
    # the other methods.
    expected_scoped_metrics = {
        "ExtraTreeRegressor": [
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.predict", 4),
            ("Function/MLModel/Sklearn/Named/ExtraTreeRegressor.score", 2),
        ],
        "DecisionTreeClassifier": [
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict", 4),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.score", 2),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/DecisionTreeClassifier.predict_proba", 4),
        ],
        "ExtraTreeClassifier": [
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict", 4),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.score", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreeClassifier.predict_proba", 4),
        ],
        "DecisionTreeRegressor": [
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.predict", 4),
            ("Function/MLModel/Sklearn/Named/DecisionTreeRegressor.score", 2),
        ],
    }

    @validate_transaction_metrics(
        "test_tree_models:test_multiple_calls_to_model_methods.<locals>._test",
        scoped_metrics=expected_scoped_metrics[tree_model_name],
        rollup_metrics=expected_scoped_metrics[tree_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        x_test = [[2.0, 2.0], [2.0, 1.0]]
        y_test = [1, 1]

        model = run_tree_model()

        model.predict(x_test)
        model.score(x_test, y_test)
        # Some models don't have these methods.
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

    _test()


@pytest.fixture(params=["ExtraTreeRegressor", "DecisionTreeClassifier", "ExtraTreeClassifier", "DecisionTreeRegressor"])
def tree_model_name(request):
    return request.param


@pytest.fixture
def run_tree_model(tree_model_name):
    def _run():
        import sklearn.tree

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[2.0, 2.0], [2.0, 1.0]]
        y_test = [1, 1]

        clf = getattr(sklearn.tree, tree_model_name)(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        model.score(x_test, y_test)
        # Some models don't have these methods.
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        return model

    return _run
