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
from sklearn import __init__  # noqa: Needed for get_package_version
from sklearn.ensemble import AdaBoostClassifier
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version
from newrelic.packages import six

SKLEARN_VERSION = tuple(map(int, get_package_version("sklearn").split(".")))


# Python 2 will not allow instantiation of abstract class
# (abstract method is __init__ here)
@pytest.mark.skipif(SKLEARN_VERSION >= (1, 0, 0) or six.PY2, reason="Requires sklearn < 1.0 and Python3")
@pytest.mark.parametrize(
    "multioutput_model_name",
    [
        "MultiOutputEstimator",
    ],
)
def test_below_v1_0_model_methods_wrapped_in_function_trace(multioutput_model_name, run_multioutput_model):
    expected_scoped_metrics = {
        "MultiOutputEstimator": [
            ("Function/MLModel/Sklearn/Named/MultiOutputEstimator.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiOutputEstimator.predict", 2),
        ],
    }
    expected_transaction_name = (
        "test_multioutput_models:test_below_v1_0_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_multioutput_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[multioutput_model_name],
        rollup_metrics=expected_scoped_metrics[multioutput_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_multioutput_model(multioutput_model_name)

    _test()


@pytest.mark.parametrize(
    "multioutput_model_name",
    [
        "MultiOutputClassifier",
        "ClassifierChain",
        "RegressorChain",
    ],
)
def test_above_v1_0_model_methods_wrapped_in_function_trace(multioutput_model_name, run_multioutput_model):
    expected_scoped_metrics = {
        "MultiOutputClassifier": [
            ("Function/MLModel/Sklearn/Named/MultiOutputClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultiOutputClassifier.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/MultiOutputClassifier.score", 1),
        ],
        "ClassifierChain": [
            ("Function/MLModel/Sklearn/Named/ClassifierChain.fit", 1),
            ("Function/MLModel/Sklearn/Named/ClassifierChain.predict_proba", 1),
        ],
        "RegressorChain": [
            ("Function/MLModel/Sklearn/Named/RegressorChain.fit", 1),
        ],
    }
    expected_transaction_name = (
        "test_multioutput_models:test_above_v1_0_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_multioutput_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[multioutput_model_name],
        rollup_metrics=expected_scoped_metrics[multioutput_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_multioutput_model(multioutput_model_name)

    _test()


@pytest.fixture
def run_multioutput_model():
    def _run(multioutput_model_name):
        import sklearn.multioutput
        from sklearn.datasets import make_multilabel_classification

        X, y = make_multilabel_classification(n_classes=3, random_state=0)

        kwargs = {"estimator": AdaBoostClassifier()}
        if multioutput_model_name in ["RegressorChain", "ClassifierChain"]:
            kwargs = {"base_estimator": AdaBoostClassifier()}
        clf = getattr(sklearn.multioutput, multioutput_model_name)(**kwargs)

        model = clf.fit(X, y)
        if hasattr(model, "predict"):
            model.predict(X)
        if hasattr(model, "score"):
            model.score(X, y)
        if hasattr(model, "predict_proba"):
            model.predict_proba(X)

        return model

    return _run
