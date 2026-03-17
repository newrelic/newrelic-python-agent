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


@pytest.mark.parametrize(
    "naive_bayes_model_name", ["BernoulliNB", "CategoricalNB", "ComplementNB", "GaussianNB", "MultinomialNB"]
)
def test_model_methods_wrapped_in_function_trace(naive_bayes_model_name, run_naive_bayes_model):
    expected_scoped_metrics = {
        "BernoulliNB": [
            ("Function/MLModel/Sklearn/Named/BernoulliNB.fit", 1),
            ("Function/MLModel/Sklearn/Named/BernoulliNB.predict", 1),
            ("Function/MLModel/Sklearn/Named/BernoulliNB.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/BernoulliNB.predict_proba", 1),
        ],
        "CategoricalNB": [
            ("Function/MLModel/Sklearn/Named/CategoricalNB.fit", 1),
            ("Function/MLModel/Sklearn/Named/CategoricalNB.predict", 1),
            ("Function/MLModel/Sklearn/Named/CategoricalNB.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/CategoricalNB.predict_proba", 1),
        ],
        "ComplementNB": [
            ("Function/MLModel/Sklearn/Named/ComplementNB.fit", 1),
            ("Function/MLModel/Sklearn/Named/ComplementNB.predict", 1),
            ("Function/MLModel/Sklearn/Named/ComplementNB.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/ComplementNB.predict_proba", 1),
        ],
        "GaussianNB": [
            ("Function/MLModel/Sklearn/Named/GaussianNB.fit", 1),
            ("Function/MLModel/Sklearn/Named/GaussianNB.predict", 1),
            ("Function/MLModel/Sklearn/Named/GaussianNB.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/GaussianNB.predict_proba", 1),
        ],
        "MultinomialNB": [
            ("Function/MLModel/Sklearn/Named/MultinomialNB.fit", 1),
            ("Function/MLModel/Sklearn/Named/MultinomialNB.predict", 1),
            ("Function/MLModel/Sklearn/Named/MultinomialNB.predict_log_proba", 2),
            ("Function/MLModel/Sklearn/Named/MultinomialNB.predict_proba", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_model_methods_wrapped_in_function_trace",
        scoped_metrics=expected_scoped_metrics[naive_bayes_model_name],
        rollup_metrics=expected_scoped_metrics[naive_bayes_model_name],
        background_task=True,
    )
    @background_task(name="test_model_methods_wrapped_in_function_trace")
    def _test():
        run_naive_bayes_model(naive_bayes_model_name)

    _test()


@pytest.fixture
def run_naive_bayes_model():
    def _run(naive_bayes_model_name):
        import sklearn.naive_bayes
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, _y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.naive_bayes, naive_bayes_model_name)()

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

        return model

    return _run
