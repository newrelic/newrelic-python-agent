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


@pytest.mark.parametrize("mixture_model_name", ["GaussianMixture", "BayesianGaussianMixture"])
def test_model_methods_wrapped_in_function_trace(mixture_model_name, run_mixture_model):
    expected_scoped_metrics = {
        "GaussianMixture": [
            ("Function/MLModel/Sklearn/Named/GaussianMixture.fit", 1),
            ("Function/MLModel/Sklearn/Named/GaussianMixture.predict", 1),
            ("Function/MLModel/Sklearn/Named/GaussianMixture.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/GaussianMixture.score", 1),
        ],
        "BayesianGaussianMixture": [
            ("Function/MLModel/Sklearn/Named/BayesianGaussianMixture.fit", 1),
            ("Function/MLModel/Sklearn/Named/BayesianGaussianMixture.predict", 1),
            ("Function/MLModel/Sklearn/Named/BayesianGaussianMixture.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/BayesianGaussianMixture.score", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_mixture_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[mixture_model_name],
        rollup_metrics=expected_scoped_metrics[mixture_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_mixture_model(mixture_model_name)

    _test()


@pytest.fixture
def run_mixture_model():
    def _run(mixture_model_name):
        import sklearn.mixture
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.mixture, mixture_model_name)()

        model = clf.fit(x_train, y_train)
        model.predict(x_test)
        model.score(x_test, y_test)
        model.predict_proba(x_test)

        return model

    return _run
