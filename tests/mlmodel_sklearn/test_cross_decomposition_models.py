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


@pytest.mark.parametrize("cross_decomposition_model_name", ["PLSRegression", "PLSSVD"])
def test_model_methods_wrapped_in_function_trace(cross_decomposition_model_name, run_cross_decomposition_model):
    expected_scoped_metrics = {
        "PLSRegression": [("Function/MLModel/Sklearn/Named/PLSRegression.fit", 1)],
        "PLSSVD": [
            ("Function/MLModel/Sklearn/Named/PLSSVD.fit", 1),
            ("Function/MLModel/Sklearn/Named/PLSSVD.transform", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_cross_decomposition_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[cross_decomposition_model_name],
        rollup_metrics=expected_scoped_metrics[cross_decomposition_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_cross_decomposition_model(cross_decomposition_model_name)

    _test()


@pytest.fixture
def run_cross_decomposition_model():
    def _run(cross_decomposition_model_name):
        import sklearn.cross_decomposition
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, _ = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {}
        if cross_decomposition_model_name == "PLSSVD":
            kwargs = {"n_components": 1}
        clf = getattr(sklearn.cross_decomposition, cross_decomposition_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
