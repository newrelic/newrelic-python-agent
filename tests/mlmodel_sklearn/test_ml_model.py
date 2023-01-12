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
from newrelic.api.ml_model import wrap_mlmodel

from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_custom_event_count,
    validate_custom_event_in_application_stats_engine,
)

from _validate_custom_events import validate_custom_events
from newrelic.api.background_task import background_task

try:
    from sklearn.tree._classes import BaseDecisionTree
except ImportError:
    from sklearn.tree.tree import BaseDecisionTree

_logger = logging.getLogger(__name__)


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
        _logger.info("Redefining fit function in custom model")
        if six.PY2:
            super(CustomTestModel, self).fit(
                X,
                y,
                sample_weight=sample_weight,
                check_input=check_input,
            )
        else:
            super().fit(
                X,
                y,
                sample_weight=sample_weight,
                check_input=check_input,
            )

        return self

    def predict(self, X, check_input=True):
        _logger.info("Redefining fit function in custom model")
        if six.PY2:
            super(CustomTestModel, self).predict(X, check_input=check_input)
        else:
            super().predict(X, check_input=check_input)


int_list_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": None,
            "type": "numerical",
            "value": "1.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": None,
            "type": "numerical",
            "value": "2.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": None,
            "type": "numerical",
            "value": "3.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyCustomModel",
            "model_version": "1.2.3",
            "feature_name": None,
            "type": "numerical",
            "value": "4.0",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_attrs_custom_model_int_list():
    @validate_custom_event_count(count=4)
    @validate_custom_events(int_list_recorded_custom_events)
    @background_task()
    def _test():
        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[1.0, 2.0], [3.0, 4.0]]

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
            "value": "5.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature1",
            "type": "categorical",
            "value": "6.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "categorical",
            "value": "7.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "PandasTestModel",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "categorical",
            "value": "8.0",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_attrs_custom_model_pandas_df():
    @validate_custom_event_count(count=4)
    @validate_custom_events(pandas_df_recorded_custom_events)
    @background_task()
    def _test():
        x_train = pandas.DataFrame({"col1": [0, 0], "col2": [1, 1]}, dtype="category")
        y_train = pandas.DataFrame({"label": [0, 1]}, dtype="category")
        x_test = pandas.DataFrame({"col1": [5.0, 6.0], "col2": [7.0, 8.0]}, dtype="category")

        model = CustomTestModel().fit(x_train, y_train)
        wrap_mlmodel(model, name="PandasTestModel", version="1.5.0b1", feature_names=["feature1", "feature2"])
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
            "value": "6.5",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "feature1",
            "type": "numerical",
            "value": "3.4",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "numerical",
            "value": "2.9",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "MyDecisionTreeClassifier",
            "model_version": "1.5.0b1",
            "feature_name": "feature2",
            "type": "numerical",
            "value": "7.5",
        }
    },
]


@reset_core_stats_engine()
def test_wrapper_attrs_builtin_model():
    @validate_custom_event_count(count=4)
    @validate_custom_events(pandas_df_recorded_builtin_events)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = pandas.DataFrame({"col1": [0, 0], "col2": [1, 1]}, dtype="int")
        y_train = pandas.DataFrame({"label": [0, 1]}, dtype="int")
        x_test = pandas.DataFrame({"col1": [6.5, 3.4], "col2": [2.9, 7.5]}, dtype="int")

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        wrap_mlmodel(model, name="MyDecisionTreeClassifier", version="1.5.0b1", feature_names=["feature1", "feature2"])
        labels = model.predict(x_test)

        return model

    _test()
