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
from sklearn.ensemble import AdaBoostClassifier
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

SKLEARN_VERSION = get_package_version_tuple("sklearn")


@pytest.mark.parametrize("semi_supervised_model_name", ["LabelPropagation", "LabelSpreading"])
def test_model_methods_wrapped_in_function_trace(semi_supervised_model_name, run_semi_supervised_model):
    expected_scoped_metrics = {
        "LabelPropagation": [
            ("Function/MLModel/Sklearn/Named/LabelPropagation.fit", 1),
            ("Function/MLModel/Sklearn/Named/LabelPropagation.predict", 2),
            ("Function/MLModel/Sklearn/Named/LabelPropagation.predict_proba", 3),
        ],
        "LabelSpreading": [
            ("Function/MLModel/Sklearn/Named/LabelSpreading.fit", 1),
            ("Function/MLModel/Sklearn/Named/LabelSpreading.predict", 2),
            ("Function/MLModel/Sklearn/Named/LabelSpreading.predict_proba", 3),
        ],
    }

    @validate_transaction_metrics(
        "test_semi_supervised_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[semi_supervised_model_name],
        rollup_metrics=expected_scoped_metrics[semi_supervised_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_semi_supervised_model(semi_supervised_model_name)

    _test()


@pytest.mark.skipif(SKLEARN_VERSION < (1, 0, 0), reason="Requires sklearn <= 1.0")
@pytest.mark.parametrize("semi_supervised_model_name", ["SelfTrainingClassifier"])
def test_above_v1_0_model_methods_wrapped_in_function_trace(semi_supervised_model_name, run_semi_supervised_model):
    expected_scoped_metrics = {
        "SelfTrainingClassifier": [
            ("Function/MLModel/Sklearn/Named/SelfTrainingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/SelfTrainingClassifier.predict", 1),
            ("Function/MLModel/Sklearn/Named/SelfTrainingClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/SelfTrainingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/SelfTrainingClassifier.predict_proba", 1),
        ]
    }

    @validate_transaction_metrics(
        "test_semi_supervised_models:test_above_v1_0_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[semi_supervised_model_name],
        rollup_metrics=expected_scoped_metrics[semi_supervised_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_semi_supervised_model(semi_supervised_model_name)

    _test()


@pytest.fixture
def run_semi_supervised_model():
    def _run(semi_supervised_model_name):
        import sklearn.semi_supervised
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        if semi_supervised_model_name == "SelfTrainingClassifier":
            kwargs = {"base_estimator": AdaBoostClassifier()}
        else:
            kwargs = {}
        clf = getattr(sklearn.semi_supervised, semi_supervised_model_name)(**kwargs)

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
