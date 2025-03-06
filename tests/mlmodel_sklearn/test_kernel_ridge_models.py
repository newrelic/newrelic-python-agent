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


@pytest.mark.parametrize("kernel_ridge_model_name", ["KernelRidge"])
def test_model_methods_wrapped_in_function_trace(kernel_ridge_model_name, run_kernel_ridge_model):
    expected_scoped_metrics = {
        "KernelRidge": [
            ("Function/MLModel/Sklearn/Named/KernelRidge.fit", 1),
            ("Function/MLModel/Sklearn/Named/KernelRidge.predict", 1),
        ]
    }

    @validate_transaction_metrics(
        "test_kernel_ridge_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[kernel_ridge_model_name],
        rollup_metrics=expected_scoped_metrics[kernel_ridge_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_kernel_ridge_model(kernel_ridge_model_name)

    _test()


@pytest.fixture
def run_kernel_ridge_model():
    def _run(kernel_ridge_model_name):
        import sklearn.kernel_ridge
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, _ = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.kernel_ridge, kernel_ridge_model_name)()

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        return model

    return _run
