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

import numpy as np
from sklearn.tree import DecisionTreeRegressor

from newrelic.api.application import Application

from newrelic.api.transaction import Transaction
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
    "test_sklearn:test_sklearn_tree",
    scoped_metrics=[
        ('ML/DecisionTreeClassifier.Predict', 1)
    ],
    background_task=True
)
@background_task()
def test_sklearn_tree():
    rng = np.random.RandomState(1)
    X = np.sort(5 * rng.rand(80, 1), axis=0)
    y = np.sin(X).ravel()
    y[::5] += 3 * (0.5 - rng.rand(16))

    regr = DecisionTreeRegressor(max_depth=2)
    regr.fit(X, y)

    X_test = np.arange(0.0, 5.0, 0.01)[:, np.newaxis]
    regr.predict(X_test)