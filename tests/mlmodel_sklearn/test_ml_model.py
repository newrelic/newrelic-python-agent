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

import logging

import pandas
import six
from _validate_custom_events import validate_custom_events
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_custom_event_count,
)

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import wrap_mlmodel

try:
    from sklearn.tree._classes import BaseDecisionTree
except ImportError:
    from sklearn.tree.tree import BaseDecisionTree

_logger = logging.getLogger(__name__)


# Create custom model that isn't auto-instrumented to validate ml_model wrapper functionality
class CustomTestModel(BaseDecisionTree):
    if six.PY2:

        def __init__(
            self,
            criterion="mse",
            splitter="random",
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            min_weight_fraction_leaf=0.0,
            max_features=None,
            random_state=0,
            max_leaf_nodes=None,
            min_impurity_decrease=0.0,
            min_impurity_split=None,
            class_weight=None,
            presort=False,
        ):
            super(CustomTestModel, self).__init__(
                criterion=criterion,
                splitter=splitter,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                min_samples_leaf=min_samples_leaf,
                min_weight_fraction_leaf=min_weight_fraction_leaf,
                max_features=max_features,
                max_leaf_nodes=max_leaf_nodes,
                class_weight=class_weight,
                random_state=random_state,
                min_impurity_decrease=min_impurity_decrease,
                min_impurity_split=min_impurity_split,
                presort=presort,
            )

    else:

        def __init__(
            self,
            criterion="poisson",
            splitter="random",
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            min_weight_fraction_leaf=0.0,
            max_features=None,
            random_state=0,
            max_leaf_nodes=None,
            min_impurity_decrease=0.0,
            class_weight=None,
            ccp_alpha=0.0,
        ):
            super().__init__(
                criterion=criterion,
                splitter=splitter,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                min_samples_leaf=min_samples_leaf,
                min_weight_fraction_leaf=min_weight_fraction_leaf,
                max_features=max_features,
                max_leaf_nodes=max_leaf_nodes,
                class_weight=class_weight,
                random_state=random_state,
                min_impurity_decrease=min_impurity_decrease,
                ccp_alpha=ccp_alpha,
            )

    def fit(self, X, y, sample_weight=None, check_input=True):
        return super(CustomTestModel, self).fit(
            X,
            y,
            sample_weight=sample_weight,
            check_input=check_input,
        )

    def predict(self, X, check_input=True):
        return super(CustomTestModel, self).predict(X, check_input=check_input)


label_value = "1.0" if six.PY2 else "0.5"
int_list_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": "0",
            "type": "numerical",
            "value": "1.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": "1",
            "type": "numerical",
            "value": "2.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "label_name": "0",
            "type": "numerical",
            "value": label_value,
        }
    },
]


@reset_core_stats_engine()
def test_custom_model_int_list_no_features_and_labels():
    @validate_custom_event_count(count=3)
    @validate_custom_events(int_list_recorded_custom_events)
    @background_task()
    def _test():
        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[1.0, 2.0]]

        model = CustomTestModel().fit(x_train, y_train)
        wrap_mlmodel(model, name="MyCustomModel", version="1.2.3")

        labels = model.predict(x_test)

        return model

    _test()


pandas_df_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature1",
            "type": "categorical",
            "value": "0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "categorical",
            "value": "0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature3",
            "type": "categorical",
            "value": "1",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "label_name": "label1",
            "type": "numerical",
            "value": "0.5",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_attrs_custom_model_pandas_df():
    @validate_custom_event_count(count=4)
    @validate_custom_events(pandas_df_recorded_custom_events)
    @background_task()
    def _test():
        x_train = pandas.DataFrame({"col1": [0, 1], "col2": [0, 1], "col3": [1, 2]}, dtype="category")
        y_train = [0, 1]
        x_test = pandas.DataFrame({"col1": [0], "col2": [0], "col3": [1]}, dtype="category")

        model = CustomTestModel().fit(x_train, y_train)
        wrap_mlmodel(
            model,
            name="PandasTestModel",
            version="1.5.0b1",
            feature_names=["feature1", "feature2", "feature3"],
            label_names=["label1"],
        )
        labels = model.predict(x_test)
        return model

    _test()


pandas_df_recorded_builtin_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "feature1",
            "type": "numerical",
            "value": "12",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "numerical",
            "value": "14",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "label_name": "label1",
            "type": "numerical",
            "value": "0",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_attrs_builtin_model():
    @validate_custom_event_count(count=3)
    @validate_custom_events(pandas_df_recorded_builtin_events)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = pandas.DataFrame({"col1": [0, 0], "col2": [1, 1]}, dtype="int")
        y_train = pandas.DataFrame({"label": [0, 1]}, dtype="int")
        x_test = pandas.DataFrame({"col1": [12], "col2": [14]}, dtype="int")

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        wrap_mlmodel(
            model,
            name="MyDecisionTreeClassifier",
            version="1.5.0b1",
            feature_names=["feature1", "feature2"],
            label_names=["label1"],
        )
        labels = model.predict(x_test)

        return model

    _test()


pandas_df_mismatched_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "col1",
            "type": "numerical",
            "value": "12",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "col2",
            "type": "numerical",
            "value": "14",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "col3",
            "type": "numerical",
            "value": "16",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "label_name": "0",
            "type": "numerical",
            "value": "1",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_mismatched_features_and_labels_df():
    @validate_custom_event_count(count=4)
    @validate_custom_events(pandas_df_mismatched_custom_events)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = pandas.DataFrame({"col1": [7, 8], "col2": [9, 10], "col3": [24, 25]}, dtype="int")
        y_train = pandas.DataFrame({"label": [0, 1]}, dtype="int")
        x_test = pandas.DataFrame({"col1": [12], "col2": [14], "col3": [16]}, dtype="int")

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        wrap_mlmodel(
            model,
            name="MyDecisionTreeClassifier",
            version="1.5.0b1",
            feature_names=["feature1", "feature2"],
            label_names=["label1", "label2"],
        )
        labels = model.predict(x_test)
        return model

    _test()


numpy_str_mismatched_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "0.0.1",
            "feature_name": "0",
            "type": "str",
            "value": "20",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "0.0.1",
            "feature_name": "1",
            "type": "str",
            "value": "21",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "0.0.1",
            "label_name": "0",
            "type": "str",
            "value": "21",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_mismatched_features_and_labels_np_array():
    @validate_custom_events(numpy_str_mismatched_custom_events)
    @validate_custom_event_count(count=3)
    @background_task()
    def _test():
        import numpy as np
        import sklearn.tree

        x_train = np.array([[20, 20], [21, 21]], dtype="<U4")
        y_train = np.array([20, 21], dtype="<U4")
        x_test = np.array([[20, 21]], dtype="<U4")
        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        wrap_mlmodel(model, name="MyDecisionTreeClassifier", version="0.0.1", feature_names=["feature1"])
        labels = model.predict(x_test)

        return model

    _test()
