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


def test_model_methods_wrapped_in_function_trace(calibration_model_name, run_calibration_model):
    expected_scoped_metrics = {
        "CalibratedClassifierCV": [
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.predict", 1),
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.predict_proba", 2),
        ]
    }

    @validate_transaction_metrics(
        "test_calibration_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[calibration_model_name],
        rollup_metrics=expected_scoped_metrics[calibration_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_calibration_model()

    _test()


@pytest.fixture(params=["CalibratedClassifierCV"])
def calibration_model_name(request):
    return request.param


@pytest.fixture
def run_calibration_model(calibration_model_name):
    def _run():
        import sklearn.calibration
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.calibration, calibration_model_name)()

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        model.predict_proba(x_test)

        return model

    return _run
