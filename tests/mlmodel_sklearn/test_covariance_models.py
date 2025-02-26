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


@pytest.mark.parametrize(
    "covariance_model_name",
    [
        "EllipticEnvelope",
        "EmpiricalCovariance",
        "GraphicalLasso",
        "GraphicalLassoCV",
        "MinCovDet",
        "ShrunkCovariance",
        "LedoitWolf",
        "OAS",
    ],
)
def test_model_methods_wrapped_in_function_trace(covariance_model_name, run_covariance_model):
    expected_scoped_metrics = {
        "EllipticEnvelope": [
            ("Function/MLModel/Sklearn/Named/EllipticEnvelope.fit", 1),
            ("Function/MLModel/Sklearn/Named/EllipticEnvelope.predict", 2),
            ("Function/MLModel/Sklearn/Named/EllipticEnvelope.score", 1),
        ],
        "EmpiricalCovariance": [
            ("Function/MLModel/Sklearn/Named/EmpiricalCovariance.fit", 1),
            ("Function/MLModel/Sklearn/Named/EmpiricalCovariance.score", 1),
        ],
        "GraphicalLasso": [("Function/MLModel/Sklearn/Named/GraphicalLasso.fit", 1)],
        "GraphicalLassoCV": [("Function/MLModel/Sklearn/Named/GraphicalLassoCV.fit", 1)],
        "MinCovDet": [("Function/MLModel/Sklearn/Named/MinCovDet.fit", 1)],
        "ShrunkCovariance": [("Function/MLModel/Sklearn/Named/ShrunkCovariance.fit", 1)],
        "LedoitWolf": [("Function/MLModel/Sklearn/Named/LedoitWolf.fit", 1)],
        "OAS": [("Function/MLModel/Sklearn/Named/OAS.fit", 1)],
    }

    @validate_transaction_metrics(
        "test_covariance_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[covariance_model_name],
        rollup_metrics=expected_scoped_metrics[covariance_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_covariance_model(covariance_model_name)

    _test()


@pytest.fixture
def run_covariance_model():
    def _run(covariance_model_name):
        import sklearn.covariance
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {}
        if covariance_model_name in ["EllipticEnvelope", "MinCovDet"]:
            kwargs = {"random_state": 0}

        clf = getattr(sklearn.covariance, covariance_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)

        return model

    return _run
