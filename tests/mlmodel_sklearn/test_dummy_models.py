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
from sklearn import __init__  # noqa: needed for get_package_version
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version
from newrelic.packages import six

SKLEARN_VERSION = tuple(map(int, get_package_version("sklearn").split(".")))


@pytest.mark.parametrize(
    "dummy_model_name",
    [
        "DummyClassifier",
        "DummyRegressor",
    ],
)
def test_model_methods_wrapped_in_function_trace(dummy_model_name, run_dummy_model):
    expected_scoped_metrics = {
        "DummyClassifier": [
            ("Function/MLModel/Sklearn/Named/DummyClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/DummyClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/DummyClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/DummyClassifier.predict_proba", 2 if SKLEARN_VERSION > (1, 0, 0) else 4),
            ("Function/MLModel/Sklearn/Named/DummyClassifier.score", 1),
        ],
        "DummyRegressor": [
            ("Function/MLModel/Sklearn/Named/DummyRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/DummyRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/DummyRegressor.score", 1),
        ],
    }

    expected_transaction_name = (
        "test_dummy_models:test_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_dummy_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[dummy_model_name],
        rollup_metrics=expected_scoped_metrics[dummy_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_dummy_model(dummy_model_name)

    _test()


@pytest.fixture
def run_dummy_model():
    def _run(dummy_model_name):
        import sklearn.dummy
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.dummy, dummy_model_name)()

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
