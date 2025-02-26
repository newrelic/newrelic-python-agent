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


@pytest.mark.parametrize("multiclass_model_name", ["OneVsRestClassifier", "OneVsOneClassifier", "OutputCodeClassifier"])
def test_model_methods_wrapped_in_function_trace(multiclass_model_name, run_multiclass_model):
    expected_scoped_metrics = {
        "OneVsRestClassifier": [
            ("Function/MLModel/Sklearn/Named/OneVsRestClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/OneVsRestClassifier.predict", 1),
            ("Function/MLModel/Sklearn/Named/OneVsRestClassifier.predict_proba", 1),
        ],
        "OneVsOneClassifier": [
            ("Function/MLModel/Sklearn/Named/OneVsOneClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/OneVsOneClassifier.predict", 1),
        ],
        "OutputCodeClassifier": [
            ("Function/MLModel/Sklearn/Named/OutputCodeClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/OutputCodeClassifier.predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_multiclass_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[multiclass_model_name],
        rollup_metrics=expected_scoped_metrics[multiclass_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_multiclass_model(multiclass_model_name)

    _test()


@pytest.fixture
def run_multiclass_model():
    def _run(multiclass_model_name):
        import sklearn.multiclass
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        # This is an example of a model that has all the available attributes
        # We could have choosen any estimator that has predict, score,
        # predict_log_proba, and predict_proba
        clf = getattr(sklearn.multiclass, multiclass_model_name)(estimator=AdaBoostClassifier())

        model = clf.fit(x_train, y_train)
        model.predict(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

        return model

    return _run
