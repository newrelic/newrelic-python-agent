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
from sklearn.neighbors import __init__  # noqa: Needed for get_package_version
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

SKLEARN_VERSION = get_package_version_tuple("sklearn")


@pytest.mark.parametrize(
    "neighbors_model_name",
    [
        "KNeighborsClassifier",
        "RadiusNeighborsClassifier",
        "KernelDensity",
        "LocalOutlierFactor",
        "NearestCentroid",
        "KNeighborsRegressor",
        "RadiusNeighborsRegressor",
        "NearestNeighbors",
    ],
)
def test_model_methods_wrapped_in_function_trace(neighbors_model_name, run_neighbors_model):
    expected_scoped_metrics = {
        "KNeighborsClassifier": [
            ("Function/MLModel/Sklearn/Named/KNeighborsClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/KNeighborsClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/KNeighborsClassifier.predict_proba", 1),
        ],
        "RadiusNeighborsClassifier": [
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsClassifier.predict", 2),
        ],
        "KernelDensity": [
            ("Function/MLModel/Sklearn/Named/KernelDensity.fit", 1),
            ("Function/MLModel/Sklearn/Named/KernelDensity.score", 1),
        ],
        "LocalOutlierFactor": [
            ("Function/MLModel/Sklearn/Named/LocalOutlierFactor.fit", 1),
            ("Function/MLModel/Sklearn/Named/LocalOutlierFactor.predict", 1),
        ],
        "NearestCentroid": [
            ("Function/MLModel/Sklearn/Named/NearestCentroid.fit", 1),
            ("Function/MLModel/Sklearn/Named/NearestCentroid.predict", 2),
        ],
        "KNeighborsRegressor": [
            ("Function/MLModel/Sklearn/Named/KNeighborsRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/KNeighborsRegressor.predict", 2),
        ],
        "RadiusNeighborsRegressor": [
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsRegressor.predict", 2),
        ],
        "NearestNeighbors": [("Function/MLModel/Sklearn/Named/NearestNeighbors.fit", 1)],
    }

    @validate_transaction_metrics(
        "test_neighbors_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[neighbors_model_name],
        rollup_metrics=expected_scoped_metrics[neighbors_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_neighbors_model(neighbors_model_name)

    _test()


@pytest.mark.skipif(SKLEARN_VERSION < (1, 0, 0), reason="Requires sklearn >= 1.0")
@pytest.mark.parametrize(
    "neighbors_model_name",
    [
        "KNeighborsTransformer",
        "RadiusNeighborsTransformer",
        "NeighborhoodComponentsAnalysis",
        "RadiusNeighborsClassifier",
    ],
)
def test_above_v1_0_model_methods_wrapped_in_function_trace(neighbors_model_name, run_neighbors_model):
    expected_scoped_metrics = {
        "KNeighborsTransformer": [
            ("Function/MLModel/Sklearn/Named/KNeighborsTransformer.fit", 1),
            ("Function/MLModel/Sklearn/Named/KNeighborsTransformer.transform", 1),
        ],
        "RadiusNeighborsTransformer": [
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsTransformer.fit", 1),
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsTransformer.transform", 1),
        ],
        "NeighborhoodComponentsAnalysis": [
            ("Function/MLModel/Sklearn/Named/NeighborhoodComponentsAnalysis.fit", 1),
            ("Function/MLModel/Sklearn/Named/NeighborhoodComponentsAnalysis.transform", 1),
        ],
        "RadiusNeighborsClassifier": [
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/RadiusNeighborsClassifier.predict_proba", 3),  # Added in v1.0
        ],
    }

    @validate_transaction_metrics(
        "test_neighbors_models:test_above_v1_0_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[neighbors_model_name],
        rollup_metrics=expected_scoped_metrics[neighbors_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_neighbors_model(neighbors_model_name)

    _test()


@pytest.fixture
def run_neighbors_model():
    def _run(neighbors_model_name):
        import sklearn.neighbors
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {}
        if neighbors_model_name == "LocalOutlierFactor":
            kwargs = {"novelty": True}
        clf = getattr(sklearn.neighbors, neighbors_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
