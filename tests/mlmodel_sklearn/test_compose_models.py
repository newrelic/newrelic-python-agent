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
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import Normalizer
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.mark.parametrize("compose_model_name", ["ColumnTransformer", "TransformedTargetRegressor"])
def test_model_methods_wrapped_in_function_trace(compose_model_name, run_compose_model):
    expected_scoped_metrics = {
        "ColumnTransformer": [
            ("Function/MLModel/Sklearn/Named/ColumnTransformer.fit", 1),
            ("Function/MLModel/Sklearn/Named/ColumnTransformer.transform", 1),
        ],
        "TransformedTargetRegressor": [
            ("Function/MLModel/Sklearn/Named/TransformedTargetRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/TransformedTargetRegressor.predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_compose_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[compose_model_name],
        rollup_metrics=expected_scoped_metrics[compose_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_compose_model(compose_model_name)

    _test()


@pytest.fixture
def run_compose_model():
    def _run(compose_model_name):
        import numpy as np
        import sklearn.compose

        if compose_model_name == "TransformedTargetRegressor":
            kwargs = {"regressor": LinearRegression()}
            X = np.arange(4).reshape(-1, 1)
            y = np.exp(2 * X).ravel()
        else:
            X = [[0.0, 1.0, 2.0, 2.0], [1.0, 1.0, 0.0, 1.0]]
            y = None
            kwargs = {
                "transformers": [
                    ("norm1", Normalizer(norm="l1"), [0, 1]),
                    ("norm2", Normalizer(norm="l1"), slice(2, 4)),
                ]
            }

        clf = getattr(sklearn.compose, compose_model_name)(**kwargs)

        model = clf.fit(X, y)
        if hasattr(model, "predict"):
            model.predict(X)
        if hasattr(model, "transform"):
            model.transform(X)

        return model

    return _run
