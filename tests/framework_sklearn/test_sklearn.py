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
from sklearn.tree import (
    DecisionTreeClassifier,
    DecisionTreeRegressor,
    ExtraTreeRegressor,
    ExtraTreeClassifier
)

from newrelic.api.application import Application

from newrelic.api.transaction import Transaction
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
    "test_sklearn:test_sklearn_tree_DecisionTreeClassifier",
    scoped_metrics=[('Function/sklearn.tree._classes:DecisionTreeClassifier.predict', 1)],
    background_task=True
)
@background_task()
def test_sklearn_tree_DecisionTreeClassifier():
    X = [[0, 0], [1, 1]]
    Y = [0, 1]
    clf = DecisionTreeClassifier()
    clf = clf.fit(X, Y)

    clf.predict([[2., 2.]])


@validate_transaction_metrics(
    "test_sklearn:test_sklearn_tree_DecisionTreeRegressor",
    scoped_metrics=[('Function/sklearn.tree._classes:DecisionTreeRegressor.predict', 1)],
    background_task=True
)
@background_task()
def test_sklearn_tree_DecisionTreeRegressor():
    X = [[0, 0], [1, 1]]
    Y = [0, 1]
    clf = DecisionTreeRegressor()
    clf = clf.fit(X, Y)

    clf.predict([[2., 2.]])


@validate_transaction_metrics(
    "test_sklearn:test_sklearn_tree_ExtraTreeRegressor",
    scoped_metrics=[('Function/sklearn.tree._classes:ExtraTreeRegressor.predict', 2)],
    background_task=True
)
@background_task()
def test_sklearn_tree_ExtraTreeRegressor():
    X = [[0, 0], [1, 1]]
    Y = [0, 1]
    clf = ExtraTreeRegressor()
    clf = clf.fit(X, Y)

    clf.predict([[2., 2.]])


@validate_transaction_metrics(
    "test_sklearn:test_sklearn_tree_ExtraTreeClassifier",
    scoped_metrics=[('Function/sklearn.tree._classes:ExtraTreeClassifier.predict', 2)],
    background_task=True
)
@background_task()
def test_sklearn_tree_ExtraTreeClassifier():
    X = [[0, 0], [1, 1]]
    Y = [0, 1]
    clf = ExtraTreeClassifier()
    clf = clf.fit(X, Y)

    clf.predict([[2., 2.]])

@validate_transaction_metrics(
    "test_sklearn:test_sklean_pipeline",
    scoped_metrics=[
        ('Function/sklearn.pipeline:Pipeline.predict', 1),
        ('Function/sklearn.svm._classes:SVC.predict', 1)
    ],
    background_task=True
)
@background_task()
def test_sklean_pipeline():
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    X, y = make_classification(random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
    pipe = Pipeline([('scaler', StandardScaler()), ('svc', SVC())])
    # The pipeline can be used as any other estimator
    # and avoids leaking the test set into the train set
    pipe.fit(X_train, y_train)
    Pipeline(steps=[('scaler', StandardScaler()), ('svc', SVC())])
    pipe.predict(X_test)

## sklearn\.([^\.]*)\.([^\.]*)\.([^\.]*)
## if module.__name__ == 'sklearn.$1':
## if hasattr(module.$2, "$3"): wrap_function_trace(module, "$2.$3")