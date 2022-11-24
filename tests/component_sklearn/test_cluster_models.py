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


def test_model_methods_wrapped_in_function_trace(cluster_model_name, run_cluster_model):
    expected_scoped_metrics = {
        "AffinityPropagation": [
            ("MLModel/Sklearn/Named/AffinityPropagation.fit", 2),
            ("MLModel/Sklearn/Named/AffinityPropagation.predict", 1),
            ("MLModel/Sklearn/Named/AffinityPropagation.fit_predict", 1),
        ],
        "AgglomerativeClustering": [
            ("MLModel/Sklearn/Named/AgglomerativeClustering.fit", 2),
            ("MLModel/Sklearn/Named/AgglomerativeClustering.fit_predict", 1),
        ],
        "Birch": [
            ("MLModel/Sklearn/Named/Birch.fit", 2),
            ("MLModel/Sklearn/Named/Birch.predict", 1),
            ("MLModel/Sklearn/Named/Birch.fit_predict", 1),
        ],
        "BisectingKMeans": [
            ("MLModel/Sklearn/Named/BisectingKMeans.fit", 2),
            ("MLModel/Sklearn/Named/BisectingKMeans.predict", 1),
            ("MLModel/Sklearn/Named/BisectingKMeans.fit_predict", 1),
        ],
        "DBSCAN": [
            ("MLModel/Sklearn/Named/DBSCAN.fit", 2),
            ("MLModel/Sklearn/Named/DBSCAN.fit_predict", 1),
        ],
        "FeatureAgglomeration": [
            ("MLModel/Sklearn/Named/FeatureAgglomeration.fit", 1),
        ],
        "KMeans": [
            ("MLModel/Sklearn/Named/KMeans.fit", 2),
            ("MLModel/Sklearn/Named/KMeans.predict", 1),
            ("MLModel/Sklearn/Named/KMeans.fit_predict", 1),
        ],
        "MeanShift": [
            ("MLModel/Sklearn/Named/MeanShift.fit", 2),
            ("MLModel/Sklearn/Named/MeanShift.predict", 1),
            ("MLModel/Sklearn/Named/MeanShift.fit_predict", 1),
        ],
        "MiniBatchKMeans": [
            ("MLModel/Sklearn/Named/MiniBatchKMeans.fit", 2),
            ("MLModel/Sklearn/Named/MiniBatchKMeans.predict", 1),
            ("MLModel/Sklearn/Named/MiniBatchKMeans.fit_predict", 1),
        ],
        "OPTICS": [
            ("MLModel/Sklearn/Named/OPTICS.fit", 2),
            ("MLModel/Sklearn/Named/OPTICS.fit_predict", 1),
        ],
        "SpectralBiclustering": [
            ("MLModel/Sklearn/Named/SpectralBiclustering.fit", 1),
        ],
        "SpectralCoclustering": [
            ("MLModel/Sklearn/Named/SpectralCoclustering.fit", 1),
        ],
        "SpectralClustering": [
            ("MLModel/Sklearn/Named/SpectralClustering.fit", 2),
            ("MLModel/Sklearn/Named/SpectralClustering.fit_predict", 1),
        ],
    }
    expected_transaction_name = "test_cluster_models:_test"
    if six.PY3:
        expected_transaction_name = "test_cluster_models:test_model_methods_wrapped_in_function_trace.<locals>._test"

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[cluster_model_name],
        rollup_metrics=expected_scoped_metrics[cluster_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_cluster_model()

    _test()


@pytest.fixture(
    params=[
        "AffinityPropagation",
        "AgglomerativeClustering",
        "Birch",
        "BisectingKMeans",
        "DBSCAN",
        "FeatureAgglomeration",
        "KMeans",
        "MeanShift",
        "MiniBatchKMeans",
        "OPTICS",
        "SpectralBiclustering",
        "SpectralCoclustering",
        "SpectralClustering",
    ]
)
def cluster_model_name(request):
    return request.param


@pytest.fixture
def run_cluster_model(cluster_model_name):
    def _run():
        import sklearn.cluster
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        # This works better with StackingClassifier and StackingRegressor models
        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        clf = getattr(sklearn.cluster, cluster_model_name)()

        model = clf.fit(x_train, y_train)

        if hasattr(model, "predict"):
            model.predict(x_test)
        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "fit_predict"):
            model.fit_predict(x_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)

        return model

    return _run
