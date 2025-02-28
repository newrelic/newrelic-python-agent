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
from newrelic.common.package_version_utils import get_package_version_tuple

SKLEARN_VERSION = get_package_version_tuple("sklearn")


@pytest.mark.parametrize("neural_network_model_name", ["MLPClassifier", "MLPRegressor", "BernoulliRBM"])
def test_model_methods_wrapped_in_function_trace(neural_network_model_name, run_neural_network_model):
    expected_scoped_metrics = {
        "MLPClassifier": [
            ("Function/MLModel/Sklearn/Named/MLPClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/MLPClassifier.predict", 1),
            ("Function/MLModel/Sklearn/Named/MLPClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/MLPClassifier.predict_proba", 2),
        ],
        "MLPRegressor": [
            ("Function/MLModel/Sklearn/Named/MLPRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/MLPRegressor.predict", 1),
        ],
        "BernoulliRBM": [
            ("Function/MLModel/Sklearn/Named/BernoulliRBM.fit", 1),
            ("Function/MLModel/Sklearn/Named/BernoulliRBM.transform", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_neural_network_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[neural_network_model_name],
        rollup_metrics=expected_scoped_metrics[neural_network_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_neural_network_model(neural_network_model_name)

    _test()


@pytest.fixture
def run_neural_network_model():
    def _run(neural_network_model_name):
        import sklearn.neural_network
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.neural_network, neural_network_model_name)()

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
