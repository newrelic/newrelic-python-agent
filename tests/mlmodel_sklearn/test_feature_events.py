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

import sys

import numpy as np
import pandas
from _validate_custom_events import validate_custom_events
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
)

from newrelic.api.background_task import background_task

pandas_df_category_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "categorical",
            "value": "2.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "categorical",
            "value": "3.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "categorical",
            "value": "4.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "categorical",
            "value": "1.0",
        }
    },
]


@reset_core_stats_engine()
def test_pandas_df_categorical_feature_event():
    @validate_custom_events(pandas_df_category_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(
            pandas.DataFrame({"col1": [0, 0], "col2": [1, 1]}, dtype="category"), pandas.DataFrame({"label": [0, 1]})
        )

        labels = model.predict(pandas.DataFrame({"col1": [2.0, 3.0], "col2": [4.0, 1.0]}, dtype="category"))
        return model

    _test()


pandas_df_bool_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "bool",
            "value": "True",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "bool",
            "value": "False",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "bool",
            "value": "True",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "bool",
            "value": "False",
        }
    },
]


@reset_core_stats_engine()
def test_pandas_df_bool_feature_event():
    @validate_custom_events(pandas_df_bool_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        dtype_name = "bool" if sys.version_info < (3, 8) else "boolean"
        x_train = pandas.DataFrame({"col1": [True, False], "col2": [True, False]}, dtype=dtype_name)
        y_train = pandas.DataFrame({"label": [True, False]}, dtype=dtype_name)
        x_test = pandas.DataFrame({"col1": [True, False], "col2": [True, False]}, dtype=dtype_name)

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


pandas_df_float_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "numerical",
            "value": "100.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "col1",
            "type": "numerical",
            "value": "200.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "numerical",
            "value": "300.0",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "col2",
            "type": "numerical",
            "value": "400.0",
        }
    },
]


@reset_core_stats_engine()
def test_pandas_df_float_feature_event():
    @validate_custom_events(pandas_df_float_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = pandas.DataFrame({"col1": [120.0, 254.0], "col2": [236.9, 234.5]}, dtype="float64")
        y_train = pandas.DataFrame({"label": [345.6, 456.7]}, dtype="float64")
        x_test = pandas.DataFrame({"col1": [100.0, 200.0], "col2": [300.0, 400.0]}, dtype="float64")

        clf = getattr(sklearn.tree, "DecisionTreeRegressor")(random_state=0)

        model = clf.fit(x_train, y_train)
        labels = model.predict(x_test)

        return model

    _test()


int_list_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "numerical",
            "value": "1",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "numerical",
            "value": "2",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "numerical",
            "value": "3",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "numerical",
            "value": "4",
        }
    },
]


@reset_core_stats_engine()
def test_int_list():
    @validate_custom_events(int_list_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[1, 2], [3, 4]]

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


numpy_int_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "numerical",
            "value": "12",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "numerical",
            "value": "13",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "numerical",
            "value": "14",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "numerical",
            "value": "15",
        }
    },
]


@reset_core_stats_engine()
def test_numpy_int_array():
    @validate_custom_events(numpy_int_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = np.array([[10, 10], [11, 11]], dtype="int")
        y_train = np.array([10, 11], dtype="int")
        x_test = np.array([[12, 13], [14, 15]], dtype="int")

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


numpy_str_recorded_custom_events = [
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "str",
            "value": "20",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "str",
            "value": "21",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "str",
            "value": "22",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "str",
            "value": "23",
        }
    },
]


@reset_core_stats_engine()
def test_numpy_str_array():
    @validate_custom_events(numpy_str_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = np.array([[20, 20], [21, 21]], dtype="<U4")
        y_train = np.array([20, 21], dtype="<U4")
        x_test = np.array([[20, 21], [22, 23]], dtype="<U4")
        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        labels = model.predict(x_test)

        return model

    _test()


numpy_str_recorded_custom_events_no_value = [
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "0",
            "type": "str",
        }
    },
    {
        "users": {
            "inference_id": None,
            "model_name": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature_name": "1",
            "type": "str",
        }
    },
]


@reset_core_stats_engine()
@override_application_settings({"machine_learning.inference_event_value.enabled": False})
def test_does_not_include_value_when_inference_event_value_enabled_is_false():
    @validate_custom_events(numpy_str_recorded_custom_events_no_value)
    @validate_custom_event_count(count=2)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = np.array([[20, 20], [21, 21]], dtype="<U4")
        y_train = np.array([20, 21], dtype="<U4")
        x_test = np.array([[20, 21]], dtype="<U4")
        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)

        model = clf.fit(x_train, y_train)
        labels = model.predict(x_test)

        return model

    _test()
