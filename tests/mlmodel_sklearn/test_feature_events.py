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

import pandas
import pytest
import numpy as np

from testing_support.fixtures import (reset_core_stats_engine,
        validate_custom_event_count,
        validate_custom_event_in_application_stats_engine,)

from newrelic.api.background_task import background_task

from _validate_custom_events import validate_custom_events


pandas_df_recorded_custom_events = [
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col1', 'type': "categorical", 'value': 2.0}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col1', 'type': "categorical", 'value': 3.0}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col2', 'type': "categorical", 'value': 4.0}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col2', 'type': "categorical", 'value': 1.0}},
]


@reset_core_stats_engine()
def test_pandas_df_feature_event():
    @validate_custom_events(pandas_df_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(pandas.DataFrame({"col1": [0, 0], "col2": [1, 1]}, dtype='category'), pandas.DataFrame({"label": [0, 1]}))

        labels = model.predict(pandas.DataFrame({"col1": [2.0, 3.0], "col2": [4.0, 1.0]}, dtype='category'))
        return model

    _test()


pandas_df_bool_recorded_custom_events = [
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col1', 'type': "bool", 'value': 'True'}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col1', 'type': "bool", 'value': 'False'}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col2', 'type': "bool", 'value': 'True'}},
    {"users": {"inference_id": None, 'model_name': 'DecisionTreeClassifier', "model_version": '0.0.0', 'feature_name': 'col2', 'type': "bool", 'value': 'False'}},
]


@reset_core_stats_engine()
def test_pandas_df_bool_feature_event():
    @validate_custom_events(pandas_df_bool_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(pandas.DataFrame({"col1": [True, False], "col2": [True, False]}, dtype='boolean'), pandas.DataFrame({"label": [True, False]}))

        labels = model.predict(pandas.DataFrame({"col1": [True, False], "col2": [True, False]}, dtype='boolean'))
        return model

    _test()



int_list_recorded_custom_events = [
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': 1}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': 2}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': 3}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': 4}},
]


@reset_core_stats_engine()
def test_int_list():
    @validate_custom_events(int_list_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit([[0, 0], [1, 1]], [0, 1])

        labels = model.predict([[1, 2], [3, 4]])
        return model

    _test()


numpy_int_recorded_custom_events = [
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': '11'}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': '10'}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': '12'}},
    {"users": {"inference_id": None, 'model_name': 'ExtraTreeRegressor', "model_version": '0.0.0', 'feature_name': None, 'type': "numerical", 'value': '13'}},
]

@reset_core_stats_engine()
def test_numpy_int_array():
    @validate_custom_events(numpy_int_recorded_custom_events)
    @validate_custom_event_count(count=4)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit(np.array([[10, 10], [11, 11]]), np.array([10, 11]))

        labels = model.predict(np.array([[11, 10], [12, 13]]))
        return model

    _test()

