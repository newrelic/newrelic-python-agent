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
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

SKLEARN_VERSION = get_package_version_tuple("sklearn")


@pytest.mark.parametrize("feature_selection_model_name", ["VarianceThreshold", "RFE", "RFECV", "SelectFromModel"])
def test_below_v1_0_model_methods_wrapped_in_function_trace(feature_selection_model_name, run_feature_selection_model):
    expected_scoped_metrics = {
        "VarianceThreshold": [("Function/MLModel/Sklearn/Named/VarianceThreshold.fit", 1)],
        "RFE": [
            ("Function/MLModel/Sklearn/Named/RFE.fit", 1),
            ("Function/MLModel/Sklearn/Named/RFE.predict", 1),
            ("Function/MLModel/Sklearn/Named/RFE.score", 1),
            ("Function/MLModel/Sklearn/Named/RFE.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/RFE.predict_proba", 1),
        ],
        "RFECV": [("Function/MLModel/Sklearn/Named/RFECV.fit", 1)],
        "SelectFromModel": [("Function/MLModel/Sklearn/Named/SelectFromModel.fit", 1)],
    }

    @validate_transaction_metrics(
        "test_feature_selection_models:test_below_v1_0_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[feature_selection_model_name],
        rollup_metrics=expected_scoped_metrics[feature_selection_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_feature_selection_model(feature_selection_model_name)

    _test()


@pytest.mark.skipif(SKLEARN_VERSION < (1, 0, 0), reason="Requires sklearn >= 1.0")
@pytest.mark.parametrize("feature_selection_model_name", ["SequentialFeatureSelector"])
def test_above_v1_0_model_methods_wrapped_in_function_trace(feature_selection_model_name, run_feature_selection_model):
    expected_scoped_metrics = {
        "SequentialFeatureSelector": [("Function/MLModel/Sklearn/Named/SequentialFeatureSelector.fit", 1)]
    }

    @validate_transaction_metrics(
        "test_feature_selection_models:test_above_v1_0_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[feature_selection_model_name],
        rollup_metrics=expected_scoped_metrics[feature_selection_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_feature_selection_model(feature_selection_model_name)

    _test()


@pytest.fixture
def run_feature_selection_model():
    def _run(feature_selection_model_name):
        import sklearn.feature_selection
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {}
        if feature_selection_model_name in ["RFE", "SequentialFeatureSelector", "SelectFromModel", "RFECV"]:
            # This is an example of a model that has all the available attributes
            # We could have choosen any estimator that has predict, score,
            # predict_log_proba, and predict_proba
            kwargs = {"estimator": AdaBoostClassifier()}
        clf = getattr(sklearn.feature_selection, feature_selection_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

        return model

    return _run
