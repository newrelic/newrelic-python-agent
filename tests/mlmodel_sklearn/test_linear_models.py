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
SCIPY_VERSION = get_package_version_tuple("scipy")


@pytest.mark.parametrize(
    "linear_model_name",
    [
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
        "Ridge",
        "RidgeCV",
        "RidgeClassifier",
        "RidgeClassifierCV",
        "TheilSenRegressor",
        "RANSACRegressor",
    ],
)
def test_model_methods_wrapped_in_function_trace(linear_model_name, run_linear_model):
    expected_scoped_metrics = {
        "ARDRegression": [
            ("Function/MLModel/Sklearn/Named/ARDRegression.fit", 1),
            ("Function/MLModel/Sklearn/Named/ARDRegression.predict", 2),
            ("Function/MLModel/Sklearn/Named/ARDRegression.score", 1),
        ],
        "BayesianRidge": [
            ("Function/MLModel/Sklearn/Named/BayesianRidge.fit", 1),
            ("Function/MLModel/Sklearn/Named/BayesianRidge.predict", 2),
            ("Function/MLModel/Sklearn/Named/BayesianRidge.score", 1),
        ],
        "ElasticNet": [
            ("Function/MLModel/Sklearn/Named/ElasticNet.fit", 1),
            ("Function/MLModel/Sklearn/Named/ElasticNet.predict", 2),
            ("Function/MLModel/Sklearn/Named/ElasticNet.score", 1),
        ],
        "ElasticNetCV": [
            ("Function/MLModel/Sklearn/Named/ElasticNetCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/ElasticNetCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/ElasticNetCV.score", 1),
        ],
        "HuberRegressor": [
            ("Function/MLModel/Sklearn/Named/HuberRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/HuberRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/HuberRegressor.score", 1),
        ],
        "Lars": [
            ("Function/MLModel/Sklearn/Named/Lars.fit", 1),
            ("Function/MLModel/Sklearn/Named/Lars.predict", 2),
            ("Function/MLModel/Sklearn/Named/Lars.score", 1),
        ],
        "LarsCV": [
            ("Function/MLModel/Sklearn/Named/LarsCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/LarsCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/LarsCV.score", 1),
        ],
        "Lasso": [
            ("Function/MLModel/Sklearn/Named/Lasso.fit", 1),
            ("Function/MLModel/Sklearn/Named/Lasso.predict", 2),
            ("Function/MLModel/Sklearn/Named/Lasso.score", 1),
        ],
        "LassoCV": [
            ("Function/MLModel/Sklearn/Named/LassoCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/LassoCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/LassoCV.score", 1),
        ],
        "LassoLars": [
            ("Function/MLModel/Sklearn/Named/LassoLars.fit", 1),
            ("Function/MLModel/Sklearn/Named/LassoLars.predict", 2),
            ("Function/MLModel/Sklearn/Named/LassoLars.score", 1),
        ],
        "LassoLarsCV": [
            ("Function/MLModel/Sklearn/Named/LassoLarsCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/LassoLarsCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/LassoLarsCV.score", 1),
        ],
        "LassoLarsIC": [
            ("Function/MLModel/Sklearn/Named/LassoLarsIC.fit", 1),
            ("Function/MLModel/Sklearn/Named/LassoLarsIC.predict", 2),
            ("Function/MLModel/Sklearn/Named/LassoLarsIC.score", 1),
        ],
        "LinearRegression": [
            ("Function/MLModel/Sklearn/Named/LinearRegression.fit", 1),
            ("Function/MLModel/Sklearn/Named/LinearRegression.predict", 2),
            ("Function/MLModel/Sklearn/Named/LinearRegression.score", 1),
        ],
        "LogisticRegression": [
            ("Function/MLModel/Sklearn/Named/LogisticRegression.fit", 1),
            ("Function/MLModel/Sklearn/Named/LogisticRegression.predict", 2),
            ("Function/MLModel/Sklearn/Named/LogisticRegression.score", 1),
        ],
        "LogisticRegressionCV": [
            ("Function/MLModel/Sklearn/Named/LogisticRegressionCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/LogisticRegressionCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/LogisticRegressionCV.score", 1),
        ],
        "MultiTaskElasticNet": [
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNet.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNet.predict", 2),
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNet.score", 1),
        ],
        "MultiTaskElasticNetCV": [
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNetCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNetCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/MultiTaskElasticNetCV.score", 1),
        ],
        "MultiTaskLasso": [
            ("Function/MLModel/Sklearn/Named/MultiTaskLasso.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiTaskLasso.predict", 2),
            ("Function/MLModel/Sklearn/Named/MultiTaskLasso.score", 1),
        ],
        "MultiTaskLassoCV": [
            ("Function/MLModel/Sklearn/Named/MultiTaskLassoCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiTaskLassoCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/MultiTaskLassoCV.score", 1),
        ],
        "OrthogonalMatchingPursuit": [
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuit.fit", 1),
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuit.predict", 2),
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuit.score", 1),
        ],
        "OrthogonalMatchingPursuitCV": [
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/OrthogonalMatchingPursuitCV.score", 1),
        ],
        "PassiveAggressiveClassifier": [
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveClassifier.score", 1),
        ],
        "PassiveAggressiveRegressor": [
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/PassiveAggressiveRegressor.score", 1),
        ],
        "Perceptron": [
            ("Function/MLModel/Sklearn/Named/Perceptron.fit", 1),
            ("Function/MLModel/Sklearn/Named/Perceptron.predict", 2),
            ("Function/MLModel/Sklearn/Named/Perceptron.score", 1),
        ],
        "Ridge": [
            ("Function/MLModel/Sklearn/Named/Ridge.fit", 1),
            ("Function/MLModel/Sklearn/Named/Ridge.predict", 2),
            ("Function/MLModel/Sklearn/Named/Ridge.score", 1),
        ],
        "RidgeCV": [
            ("Function/MLModel/Sklearn/Named/RidgeCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/RidgeCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/RidgeCV.score", 1),
        ],
        "RidgeClassifier": [
            ("Function/MLModel/Sklearn/Named/RidgeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/RidgeClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/RidgeClassifier.score", 1),
        ],
        "RidgeClassifierCV": [
            ("Function/MLModel/Sklearn/Named/RidgeClassifierCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/RidgeClassifierCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/RidgeClassifierCV.score", 1),
        ],
        "TheilSenRegressor": [
            ("Function/MLModel/Sklearn/Named/TheilSenRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/TheilSenRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/TheilSenRegressor.score", 1),
        ],
        "RANSACRegressor": [
            ("Function/MLModel/Sklearn/Named/RANSACRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/RANSACRegressor.predict", 1),
            ("Function/MLModel/Sklearn/Named/RANSACRegressor.score", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_linear_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[linear_model_name],
        rollup_metrics=expected_scoped_metrics[linear_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_linear_model(linear_model_name)

    _test()


@pytest.mark.skipif(SKLEARN_VERSION < (1, 1, 0), reason="Requires sklearn >= v1.1")
@pytest.mark.parametrize(
    "linear_model_name",
    [
        "PoissonRegressor",
        "GammaRegressor",
        "TweedieRegressor",
        "QuantileRegressor",
        "SGDClassifier",
        "SGDRegressor",
        "SGDOneClassSVM",
    ],
)
def test_above_v1_1_model_methods_wrapped_in_function_trace(linear_model_name, run_linear_model):
    expected_scoped_metrics = {
        "PoissonRegressor": [
            ("Function/MLModel/Sklearn/Named/PoissonRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/PoissonRegressor.predict", 1),
            ("Function/MLModel/Sklearn/Named/PoissonRegressor.score", 1),
        ],
        "GammaRegressor": [
            ("Function/MLModel/Sklearn/Named/GammaRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/GammaRegressor.predict", 1),
            ("Function/MLModel/Sklearn/Named/GammaRegressor.score", 1),
        ],
        "TweedieRegressor": [
            ("Function/MLModel/Sklearn/Named/TweedieRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/TweedieRegressor.predict", 1),
            ("Function/MLModel/Sklearn/Named/TweedieRegressor.score", 1),
        ],
        "QuantileRegressor": [
            ("Function/MLModel/Sklearn/Named/QuantileRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/QuantileRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/QuantileRegressor.score", 1),
        ],
        "SGDClassifier": [
            ("Function/MLModel/Sklearn/Named/SGDClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/SGDClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/SGDClassifier.score", 1),
        ],
        "SGDRegressor": [
            ("Function/MLModel/Sklearn/Named/SGDRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/SGDRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/SGDRegressor.score", 1),
        ],
        "SGDOneClassSVM": [
            ("Function/MLModel/Sklearn/Named/SGDOneClassSVM.fit", 1),
            ("Function/MLModel/Sklearn/Named/SGDOneClassSVM.predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_linear_models:test_above_v1_1_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[linear_model_name],
        rollup_metrics=expected_scoped_metrics[linear_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_linear_model(linear_model_name)

    _test()


@pytest.fixture
def run_linear_model():
    def _run(linear_model_name):
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

        if linear_model_name == "QuantileRegressor" and SCIPY_VERSION > (1, 11, 0):
            # Silence warnings and errors related to solver change
            clf.solver = "highs"

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        if hasattr(model, "score"):
            model.score(x_test, y_test)

        return model

    return _run
