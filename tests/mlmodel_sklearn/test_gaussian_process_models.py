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


@pytest.mark.parametrize(
    "gaussian_process_model_name",
    [
        "GaussianProcessClassifier",
        "GaussianProcessRegressor",
    ],
)
def test_model_methods_wrapped_in_function_trace(gaussian_process_model_name, run_gaussian_process_model):
    expected_scoped_metrics = {
        "GaussianProcessClassifier": [
            ("Function/MLModel/Sklearn/Named/GaussianProcessClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/GaussianProcessClassifier.predict", 1),
            ("Function/MLModel/Sklearn/Named/GaussianProcessClassifier.predict_proba", 1),
        ],
        "GaussianProcessRegressor": [
            ("Function/MLModel/Sklearn/Named/GaussianProcessRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/GaussianProcessRegressor.predict", 1),
        ],
    }

    expected_transaction_name = (
        "test_gaussian_process_models:test_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_gaussian_process_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[gaussian_process_model_name],
        rollup_metrics=expected_scoped_metrics[gaussian_process_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_gaussian_process_model(gaussian_process_model_name)

    _test()


@pytest.fixture
def run_gaussian_process_model():
    def _run(gaussian_process_model_name):
        import sklearn.gaussian_process
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.gaussian_process, gaussian_process_model_name)(random_state=0)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

        return model

    return _run
