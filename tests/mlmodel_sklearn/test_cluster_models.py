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


@pytest.mark.parametrize(
    "cluster_model_name",
    [
        "AffinityPropagation",
        "AgglomerativeClustering",
        "Birch",
        "DBSCAN",
        "FeatureAgglomeration",
        "KMeans",
        "MeanShift",
        "MiniBatchKMeans",
        "SpectralBiclustering",
        "SpectralCoclustering",
        "SpectralClustering",
    ],
)
def test_below_v1_1_model_methods_wrapped_in_function_trace(cluster_model_name, run_cluster_model):
    expected_scoped_metrics = {
        "AffinityPropagation": [
            ("Function/MLModel/Sklearn/Named/AffinityPropagation.fit", 2),
            ("Function/MLModel/Sklearn/Named/AffinityPropagation.predict", 1),
            ("Function/MLModel/Sklearn/Named/AffinityPropagation.fit_predict", 1),
        ],
        "AgglomerativeClustering": [
            ("Function/MLModel/Sklearn/Named/AgglomerativeClustering.fit", 2),
            ("Function/MLModel/Sklearn/Named/AgglomerativeClustering.fit_predict", 1),
        ],
        "Birch": [
            ("Function/MLModel/Sklearn/Named/Birch.fit", 2),
            ("Function/MLModel/Sklearn/Named/Birch.predict", 1 if SKLEARN_VERSION >= (1, 0, 0) else 3),
            ("Function/MLModel/Sklearn/Named/Birch.fit_predict", 1),
            ("Function/MLModel/Sklearn/Named/Birch.transform", 1),
        ],
        "DBSCAN": [
            ("Function/MLModel/Sklearn/Named/DBSCAN.fit", 2),
            ("Function/MLModel/Sklearn/Named/DBSCAN.fit_predict", 1),
        ],
        "FeatureAgglomeration": [
            ("Function/MLModel/Sklearn/Named/FeatureAgglomeration.fit", 1),
            ("Function/MLModel/Sklearn/Named/FeatureAgglomeration.transform", 1),
        ],
        "KMeans": [
            ("Function/MLModel/Sklearn/Named/KMeans.fit", 2),
            ("Function/MLModel/Sklearn/Named/KMeans.predict", 1),
            ("Function/MLModel/Sklearn/Named/KMeans.fit_predict", 1),
            ("Function/MLModel/Sklearn/Named/KMeans.transform", 1),
        ],
        "MeanShift": [
            ("Function/MLModel/Sklearn/Named/MeanShift.fit", 2),
            ("Function/MLModel/Sklearn/Named/MeanShift.predict", 1),
            ("Function/MLModel/Sklearn/Named/MeanShift.fit_predict", 1),
        ],
        "MiniBatchKMeans": [
            ("Function/MLModel/Sklearn/Named/MiniBatchKMeans.fit", 2),
            ("Function/MLModel/Sklearn/Named/MiniBatchKMeans.predict", 1),
            ("Function/MLModel/Sklearn/Named/MiniBatchKMeans.fit_predict", 1),
        ],
        "SpectralBiclustering": [("Function/MLModel/Sklearn/Named/SpectralBiclustering.fit", 1)],
        "SpectralCoclustering": [("Function/MLModel/Sklearn/Named/SpectralCoclustering.fit", 1)],
        "SpectralClustering": [
            ("Function/MLModel/Sklearn/Named/SpectralClustering.fit", 2),
            ("Function/MLModel/Sklearn/Named/SpectralClustering.fit_predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_cluster_models:test_below_v1_1_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[cluster_model_name],
        rollup_metrics=expected_scoped_metrics[cluster_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_cluster_model(cluster_model_name)

    _test()


@pytest.mark.skipif(SKLEARN_VERSION < (1, 1, 0), reason="Requires sklearn > 1.1")
@pytest.mark.parametrize("cluster_model_name", ["BisectingKMeans", "OPTICS"])
def test_above_v1_1_model_methods_wrapped_in_function_trace(cluster_model_name, run_cluster_model):
    expected_scoped_metrics = {
        "BisectingKMeans": [
            ("Function/MLModel/Sklearn/Named/BisectingKMeans.fit", 2),
            ("Function/MLModel/Sklearn/Named/BisectingKMeans.predict", 1),
            ("Function/MLModel/Sklearn/Named/BisectingKMeans.fit_predict", 1),
        ],
        "OPTICS": [
            ("Function/MLModel/Sklearn/Named/OPTICS.fit", 2),
            ("Function/MLModel/Sklearn/Named/OPTICS.fit_predict", 1),
        ],
    }

    @validate_transaction_metrics(
        "test_cluster_models:test_above_v1_1_model_methods_wrapped_in_function_trace.<locals>._test",
        scoped_metrics=expected_scoped_metrics[cluster_model_name],
        rollup_metrics=expected_scoped_metrics[cluster_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_cluster_model(cluster_model_name)

    _test()


@pytest.fixture
def run_cluster_model():
    def _run(cluster_model_name):
        import sklearn.cluster
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

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
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
