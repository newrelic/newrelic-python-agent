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
from testing_support.fixtures import validate_transaction_metrics

from newrelic.api.background_task import background_task


@validate_transaction_metrics(
    "test_sklearn:test_model_methods_wrapped_in_function_trace",
    scoped_metrics=[("Function/sklearn:Connection.__exit__", 1)],
    background_task=True,
)
@background_task()
def test_model_methods_wrapped_in_function_trace(extra_tree_regressor):
    extra_tree_regressor()


@pytest.fixture
def nearest_centroid():
    def _run():
        import numpy as np
        from sklearn.neighbors import NearestCentroid

        X = np.array([[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]])
        y = np.array([1, 1, 1, 2, 2, 2])
        clf = NearestCentroid()
        clf.fit(X, y)
        NearestCentroid()
        labels = clf.predict([[-0.8, -1]])

    return _run


@pytest.fixture
def extra_tree_regressor():
    def _run():
        from sklearn.datasets import load_diabetes
        from sklearn.ensemble import BaggingRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.tree import ExtraTreeRegressor

        X, y = load_diabetes(return_X_y=True)
        X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
        extra_tree = ExtraTreeRegressor(random_state=0)
        reg = BaggingRegressor(extra_tree, random_state=0).fit(X_train, y_train)
        reg.score(X_test, y_test)

    return _run
