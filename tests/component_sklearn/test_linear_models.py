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


def test_model_methods_wrapped_in_function_trace(linear_model_name, run_linear_model):
    expected_scoped_metrics = {
        "ARDRegression": [
            ("MLModel/Sklearn/Named/ARDRegression.fit", 1),
            ("MLModel/Sklearn/Named/ARDRegression.predict", 2),
            ("MLModel/Sklearn/Named/ARDRegression.score", 1),
        ],
        "BayesianRidge": [
            ("MLModel/Sklearn/Named/BayesianRidge.fit", 1),
            ("MLModel/Sklearn/Named/BayesianRidge.predict", 2),
            ("MLModel/Sklearn/Named/BayesianRidge.score", 1),
        ],
        "ElasticNet": [
            ("MLModel/Sklearn/Named/ElasticNet.fit", 1),
            ("MLModel/Sklearn/Named/ElasticNet.predict", 2),
            ("MLModel/Sklearn/Named/ElasticNet.score", 1),
        ],
        "ElasticNetCV": [
            ("MLModel/Sklearn/Named/ElasticNetCV.fit", 1),
            ("MLModel/Sklearn/Named/ElasticNetCV.predict", 2),
            ("MLModel/Sklearn/Named/ElasticNetCV.score", 1),
        ],
        "HuberRegressor": [
            ("MLModel/Sklearn/Named/HuberRegressor.fit", 1),
            ("MLModel/Sklearn/Named/HuberRegressor.predict", 2),
            ("MLModel/Sklearn/Named/HuberRegressor.score", 1),
        ],
        "Lars": [
            ("MLModel/Sklearn/Named/Lars.fit", 1),
            ("MLModel/Sklearn/Named/Lars.predict", 2),
            ("MLModel/Sklearn/Named/Lars.score", 1),
        ],
        "LarsCV": [
            ("MLModel/Sklearn/Named/LarsCV.fit", 1),
            ("MLModel/Sklearn/Named/LarsCV.predict", 2),
            ("MLModel/Sklearn/Named/LarsCV.score", 1),
        ],
        "Lasso": [
            ("MLModel/Sklearn/Named/Lasso.fit", 1),
            ("MLModel/Sklearn/Named/Lasso.predict", 2),
            ("MLModel/Sklearn/Named/Lasso.score", 1),
        ],
        "LassoCV": [
            ("MLModel/Sklearn/Named/LassoCV.fit", 1),
            ("MLModel/Sklearn/Named/LassoCV.predict", 2),
            ("MLModel/Sklearn/Named/LassoCV.score", 1),
        ],
        "LassoLars": [
            ("MLModel/Sklearn/Named/LassoLars.fit", 1),
            ("MLModel/Sklearn/Named/LassoLars.predict", 2),
            ("MLModel/Sklearn/Named/LassoLars.score", 1),
        ],
        "LassoLarsCV": [
            ("MLModel/Sklearn/Named/LassoLarsCV.fit", 1),
            ("MLModel/Sklearn/Named/LassoLarsCV.predict", 2),
            ("MLModel/Sklearn/Named/LassoLarsCV.score", 1),
        ],
        "LassoLarsIC": [
            ("MLModel/Sklearn/Named/LassoLarsIC.fit", 1),
            ("MLModel/Sklearn/Named/LassoLarsIC.predict", 2),
            ("MLModel/Sklearn/Named/LassoLarsIC.score", 1),
        ],
        "LinearRegression": [
            ("MLModel/Sklearn/Named/LinearRegression.fit", 1),
            ("MLModel/Sklearn/Named/LinearRegression.predict", 2),
            ("MLModel/Sklearn/Named/LinearRegression.score", 1),
        ],
        "LogisticRegression": [
            ("MLModel/Sklearn/Named/LogisticRegression.fit", 1),
            ("MLModel/Sklearn/Named/LogisticRegression.predict", 2),
            ("MLModel/Sklearn/Named/LogisticRegression.score", 1),
        ],
        "LogisticRegressionCV": [
            ("MLModel/Sklearn/Named/LogisticRegressionCV.fit", 1),
            ("MLModel/Sklearn/Named/LogisticRegressionCV.predict", 2),
            ("MLModel/Sklearn/Named/LogisticRegressionCV.score", 1),
        ],
        "MultiTaskElasticNet": [
            ("MLModel/Sklearn/Named/MultiTaskElasticNet.fit", 1),
            ("MLModel/Sklearn/Named/MultiTaskElasticNet.predict", 2),
            ("MLModel/Sklearn/Named/MultiTaskElasticNet.score", 1),
        ],
        "MultiTaskElasticNetCV": [
            ("MLModel/Sklearn/Named/MultiTaskElasticNetCV.fit", 1),
            ("MLModel/Sklearn/Named/MultiTaskElasticNetCV.predict", 2),
            ("MLModel/Sklearn/Named/MultiTaskElasticNetCV.score", 1),
        ],
        "MultiTaskLasso": [
            ("MLModel/Sklearn/Named/MultiTaskLasso.fit", 1),
            ("MLModel/Sklearn/Named/MultiTaskLasso.predict", 2),
            ("MLModel/Sklearn/Named/MultiTaskLasso.score", 1),
        ],
        "MultiTaskLassoCV": [
            ("MLModel/Sklearn/Named/MultiTaskLassoCV.fit", 1),
            ("MLModel/Sklearn/Named/MultiTaskLassoCV.predict", 2),
            ("MLModel/Sklearn/Named/MultiTaskLassoCV.score", 1),
        ],
        "OrthogonalMatchingPursuit": [
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuit.fit", 1),
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuit.predict", 2),
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuit.score", 1),
        ],
        "OrthogonalMatchingPursuitCV": [
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.fit", 1),
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.predict", 2),
            ("MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.score", 1),
        ],
        "PassiveAggressiveClassifier": [
            ("MLModel/Sklearn/Named/PassiveAggressiveClassifier.fit", 1),
            ("MLModel/Sklearn/Named/PassiveAggressiveClassifier.predict", 2),
            ("MLModel/Sklearn/Named/PassiveAggressiveClassifier.score", 1),
        ],
        "PassiveAggressiveRegressor": [
            ("MLModel/Sklearn/Named/PassiveAggressiveRegressor.fit", 1),
            ("MLModel/Sklearn/Named/PassiveAggressiveRegressor.predict", 2),
            ("MLModel/Sklearn/Named/PassiveAggressiveRegressor.score", 1),
        ],
        "Perceptron": [
            ("MLModel/Sklearn/Named/Perceptron.fit", 1),
            ("MLModel/Sklearn/Named/Perceptron.predict", 2),
            ("MLModel/Sklearn/Named/Perceptron.score", 1),
        ],
        "QuantileRegressor": [
            ("MLModel/Sklearn/Named/QuantileRegressor.fit", 1),
            ("MLModel/Sklearn/Named/QuantileRegressor.predict", 2),
            ("MLModel/Sklearn/Named/QuantileRegressor.score", 1),
        ],
        "Ridge": [
            ("MLModel/Sklearn/Named/Ridge.fit", 1),
            ("MLModel/Sklearn/Named/Ridge.predict", 2),
            ("MLModel/Sklearn/Named/Ridge.score", 1),
        ],
        "RidgeCV": [
            ("MLModel/Sklearn/Named/RidgeCV.fit", 1),
            ("MLModel/Sklearn/Named/RidgeCV.predict", 2),
            ("MLModel/Sklearn/Named/RidgeCV.score", 1),
        ],
        "RidgeClassifier": [
            ("MLModel/Sklearn/Named/RidgeClassifier.fit", 1),
            ("MLModel/Sklearn/Named/RidgeClassifier.predict", 2),
            ("MLModel/Sklearn/Named/RidgeClassifier.score", 1),
        ],
        "RidgeClassifierCV": [
            ("MLModel/Sklearn/Named/RidgeClassifierCV.fit", 1),
            ("MLModel/Sklearn/Named/RidgeClassifierCV.predict", 2),
            ("MLModel/Sklearn/Named/RidgeClassifierCV.score", 1),
        ],
        "SGDClassifier": [
            ("MLModel/Sklearn/Named/SGDClassifier.fit", 1),
            ("MLModel/Sklearn/Named/SGDClassifier.predict", 2),
            ("MLModel/Sklearn/Named/SGDClassifier.score", 1),
        ],
        "SGDRegressor": [
            ("MLModel/Sklearn/Named/SGDRegressor.fit", 1),
            ("MLModel/Sklearn/Named/SGDRegressor.predict", 2),
            ("MLModel/Sklearn/Named/SGDRegressor.score", 1),
        ],
        "SGDOneClassSVM": [
            ("MLModel/Sklearn/Named/SGDOneClassSVM.fit", 1),
            ("MLModel/Sklearn/Named/SGDOneClassSVM.predict", 1),
        ],
        "TheilSenRegressor": [
            ("MLModel/Sklearn/Named/TheilSenRegressor.fit", 1),
            ("MLModel/Sklearn/Named/TheilSenRegressor.predict", 2),
            ("MLModel/Sklearn/Named/TheilSenRegressor.score", 1),
        ],
        "RANSACRegressor": [
            ("MLModel/Sklearn/Named/RANSACRegressor.fit", 1),
            ("MLModel/Sklearn/Named/RANSACRegressor.predict", 1),
            ("MLModel/Sklearn/Named/RANSACRegressor.score", 1),
        ],
        "PoissonRegressor": [
            ("MLModel/Sklearn/Named/PoissonRegressor.fit", 1),
            ("MLModel/Sklearn/Named/PoissonRegressor.predict", 1),
            ("MLModel/Sklearn/Named/PoissonRegressor.score", 1),
        ],
        "GammaRegressor": [
            ("MLModel/Sklearn/Named/GammaRegressor.fit", 1),
            ("MLModel/Sklearn/Named/GammaRegressor.predict", 1),
            ("MLModel/Sklearn/Named/GammaRegressor.score", 1),
        ],
        "TweedieRegressor": [
            ("MLModel/Sklearn/Named/TweedieRegressor.fit", 1),
            ("MLModel/Sklearn/Named/TweedieRegressor.predict", 1),
            ("MLModel/Sklearn/Named/TweedieRegressor.score", 1),
        ],
    }
    expected_transaction_name = "test_linear_models:_test"
    if six.PY3:
        expected_transaction_name = "test_linear_models:test_model_methods_wrapped_in_function_trace.<locals>._test"

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[linear_model_name],
        rollup_metrics=expected_scoped_metrics[linear_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_linear_model()

    _test()


@pytest.fixture(
    params=[
        "ARDRegression",
        "BayesianRidge",
        "ElasticNet",
        "ElasticNetCV",
        "HuberRegressor",
        "Lars",
        "LarsCV",
        "Lasso",
        "LassoCV",
        "LassoLars",
        "LassoLarsCV",
        "LassoLarsIC",
        "LinearRegression",
        "LogisticRegression",
        "LogisticRegressionCV",
        "MultiTaskElasticNet",
        "MultiTaskElasticNetCV",
        "MultiTaskLasso",
        "MultiTaskLassoCV",
        "OrthogonalMatchingPursuit",
        "OrthogonalMatchingPursuitCV",
        "PassiveAggressiveClassifier",
        "PassiveAggressiveRegressor",
        "Perceptron",
        "QuantileRegressor",
        "Ridge",
        "RidgeCV",
        "RidgeClassifier",
        "RidgeClassifierCV",
        "SGDClassifier",
        "SGDRegressor",
        "SGDOneClassSVM",
        "TheilSenRegressor",
        "RANSACRegressor",
        "PoissonRegressor",
        "GammaRegressor",
        "TweedieRegressor",
    ]
)
def linear_model_name(request):
    return request.param


@pytest.fixture
def run_linear_model(linear_model_name):
    def _run():
        import sklearn.linear_model
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        if linear_model_name == "GammaRegressor":
            x_train = [[1, 2], [2, 3], [3, 4], [4, 3]]
            y_train = [19, 26, 33, 30]
            x_test = [[1, 2], [2, 3], [3, 4], [4, 3]]
            y_test = [19, 26, 33, 30]
        elif linear_model_name in [
            "MultiTaskElasticNet",
            "MultiTaskElasticNetCV",
            "MultiTaskLasso",
            "MultiTaskLassoCV",
        ]:
            y_train = x_train
            y_test = x_test

        clf = getattr(sklearn.linear_model, linear_model_name)()

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        if hasattr(model, "score"):
            model.score(x_test, y_test)

        return model

    return _run
