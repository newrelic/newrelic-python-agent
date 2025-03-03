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


@pytest.mark.parametrize("svm_model_name", ["LinearSVC", "LinearSVR", "SVC", "NuSVC", "SVR", "NuSVR", "OneClassSVM"])
def test_model_methods_wrapped_in_function_trace(svm_model_name, run_svm_model):
    expected_scoped_metrics = {
        "LinearSVC": [
            ("Function/MLModel/Sklearn/Named/LinearSVC.fit", 1),
            ("Function/MLModel/Sklearn/Named/LinearSVC.predict", 1),
        ],
        "LinearSVR": [
            ("Function/MLModel/Sklearn/Named/LinearSVR.fit", 1),
            ("Function/MLModel/Sklearn/Named/LinearSVR.predict", 1),
        ],
        "SVC": [("Function/MLModel/Sklearn/Named/SVC.fit", 1), ("Function/MLModel/Sklearn/Named/SVC.predict", 1)],
        "NuSVC": [("Function/MLModel/Sklearn/Named/NuSVC.fit", 1), ("Function/MLModel/Sklearn/Named/NuSVC.predict", 1)],
        "SVR": [("Function/MLModel/Sklearn/Named/SVR.fit", 1), ("Function/MLModel/Sklearn/Named/SVR.predict", 1)],
        "NuSVR": [("Function/MLModel/Sklearn/Named/NuSVR.fit", 1), ("Function/MLModel/Sklearn/Named/NuSVR.predict", 1)],
        "OneClassSVM": [
            ("Function/MLModel/Sklearn/Named/OneClassSVM.fit", 1),
            ("Function/MLModel/Sklearn/Named/OneClassSVM.predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_svm_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[svm_model_name],
        rollup_metrics=expected_scoped_metrics[svm_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_svm_model(svm_model_name)

    _test()


@pytest.fixture
def run_svm_model():
    def _run(svm_model_name):
        import sklearn.svm
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {"random_state": 0}
        if svm_model_name in ["SVR", "NuSVR", "OneClassSVM"]:
            kwargs = {}
        clf = getattr(sklearn.svm, svm_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        return model

    return _run
