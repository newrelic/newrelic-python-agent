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
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

SKLEARN_VERSION = get_package_version_tuple("sklearn")


@pytest.mark.parametrize("pipeline_model_name", ["Pipeline", "FeatureUnion"])
def test_model_methods_wrapped_in_function_trace(pipeline_model_name, run_pipeline_model):
    expected_scoped_metrics = {
        "Pipeline": [
            ("Function/MLModel/Sklearn/Named/Pipeline.fit", 1),
            ("Function/MLModel/Sklearn/Named/Pipeline.predict", 1),
            ("Function/MLModel/Sklearn/Named/Pipeline.score", 1),
        ],
        "FeatureUnion": [
            ("Function/MLModel/Sklearn/Named/FeatureUnion.fit", 1),
            ("Function/MLModel/Sklearn/Named/FeatureUnion.transform", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_pipeline_models:test_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[pipeline_model_name],
        rollup_metrics=expected_scoped_metrics[pipeline_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_pipeline_model(pipeline_model_name)

    _test()


@pytest.fixture
def run_pipeline_model():
    def _run(pipeline_model_name):
        import sklearn.pipeline
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        if pipeline_model_name == "Pipeline":
            kwargs = {"steps": [("scaler", StandardScaler()), ("svc", SVC())]}
        else:
            kwargs = {"transformer_list": [("scaler", StandardScaler()), ("svd", TruncatedSVD(n_components=2))]}
        clf = getattr(sklearn.pipeline, pipeline_model_name)(**kwargs)

        model = clf.fit(x_train, y_train)
        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
