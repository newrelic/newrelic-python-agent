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


@pytest.mark.parametrize(
    "discriminant_analysis_model_name",
    [
        "LinearDiscriminantAnalysis",
        "QuadraticDiscriminantAnalysis",
    ],
)
def test_model_methods_wrapped_in_function_trace(discriminant_analysis_model_name, run_discriminant_analysis_model):
    expected_scoped_metrics = {
        "LinearDiscriminantAnalysis": [
            ("Function/MLModel/Sklearn/Named/LinearDiscriminantAnalysis.fit", 1),
            ("Function/MLModel/Sklearn/Named/LinearDiscriminantAnalysis.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/LinearDiscriminantAnalysis.predict_proba", 2),
            ("Function/MLModel/Sklearn/Named/LinearDiscriminantAnalysis.transform", 1),
        ],
        "QuadraticDiscriminantAnalysis": [
            ("Function/MLModel/Sklearn/Named/QuadraticDiscriminantAnalysis.fit", 1),
            ("Function/MLModel/Sklearn/Named/QuadraticDiscriminantAnalysis.predict", 1),
            ("Function/MLModel/Sklearn/Named/QuadraticDiscriminantAnalysis.predict_proba", 2),
            ("Function/MLModel/Sklearn/Named/QuadraticDiscriminantAnalysis.predict_log_proba", 1),
        ],
    }

    expected_transaction_name = (
        "test_discriminant_analysis_models:test_model_methods_wrapped_in_function_trace.<locals>._test"
        if six.PY3
        else "test_discriminant_analysis_models:_test"
    )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[discriminant_analysis_model_name],
        rollup_metrics=expected_scoped_metrics[discriminant_analysis_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_discriminant_analysis_model(discriminant_analysis_model_name)

    _test()


@pytest.fixture
def run_discriminant_analysis_model():
    def _run(discriminant_analysis_model_name):
        import sklearn.discriminant_analysis
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        kwargs = {}
        clf = getattr(sklearn.discriminant_analysis, discriminant_analysis_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
