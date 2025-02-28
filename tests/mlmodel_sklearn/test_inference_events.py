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
import pandas as pd
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events

from newrelic.api.background_task import background_task

pandas_df_category_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature.col1": 2.0,
            "feature.col2": 4.0,
            "label.0": "27.0",
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_pandas_df_categorical_feature_event():
    @validate_ml_events(pandas_df_category_recorded_custom_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        import sklearn.tree

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(
            pd.DataFrame({"col1": [27.0, 24.0], "col2": [23.0, 25.0]}, dtype="category"),
            pd.DataFrame({"label": [27.0, 28.0]}),
        )

        labels = model.predict(pd.DataFrame({"col1": [2.0], "col2": [4.0]}, dtype="category"))
        return model

    _test()


label_type = "bool" if sys.version_info < (3, 8) else "numeric"
true_label_value = "True" if sys.version_info < (3, 8) else "1.0"
false_label_value = "False" if sys.version_info < (3, 8) else "0.0"
pandas_df_bool_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature.col1": True,
            "feature.col2": True,
            "label.0": true_label_value,
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_pandas_df_bool_feature_event():
    @validate_ml_events(pandas_df_bool_recorded_custom_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        import sklearn.tree

        dtype_name = "bool" if sys.version_info < (3, 8) else "boolean"
        x_train = pd.DataFrame({"col1": [True, False], "col2": [True, False]}, dtype=dtype_name)
        y_train = pd.DataFrame({"label": [True, False]}, dtype=dtype_name)
        x_test = pd.DataFrame({"col1": [True], "col2": [True]}, dtype=dtype_name)

        clf = getattr(sklearn.tree, "DecisionTreeClassifier")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


pandas_df_float_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeRegressor",
            "model_version": "0.0.0",
            "feature.col1": 100.0,
            "feature.col2": 300.0,
            "label.0": "345.6",
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_pandas_df_float_feature_event():
    @validate_ml_events(pandas_df_float_recorded_custom_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = pd.DataFrame({"col1": [120.0, 254.0], "col2": [236.9, 234.5]}, dtype="float64")
        y_train = pd.DataFrame({"label": [345.6, 456.7]}, dtype="float64")
        x_test = pd.DataFrame({"col1": [100.0], "col2": [300.0]}, dtype="float64")

        clf = getattr(sklearn.tree, "DecisionTreeRegressor")(random_state=0)

        model = clf.fit(x_train, y_train)
        labels = model.predict(x_test)

        return model

    _test()


int_list_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature.0": 1,
            "feature.1": 2,
            "label.0": "1.0",
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_int_list():
    @validate_ml_events(int_list_recorded_custom_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = [[0, 0], [1, 1]]
        y_train = [0, 1]
        x_test = [[1, 2]]

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


numpy_int_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "ExtraTreeRegressor",
            "model_version": "0.0.0",
            "feature.0": 12,
            "feature.1": 13,
            "label.0": "11.0",
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_numpy_int_array():
    @validate_ml_events(numpy_int_recorded_custom_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        import sklearn.tree

        x_train = np.array([[10, 10], [11, 11]], dtype="int")
        y_train = np.array([10, 11], dtype="int")
        x_test = np.array([[12, 13]], dtype="int")

        clf = getattr(sklearn.tree, "ExtraTreeRegressor")(random_state=0)
        model = clf.fit(x_train, y_train)

        labels = model.predict(x_test)
        return model

    _test()


numpy_str_recorded_custom_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature.0": "20",
            "feature.1": "21",
            "label.0": "21",
            "new_relic_data_schema_version": 2,
        },
    ),
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "feature.0": "22",
            "feature.1": "23",
            "label.0": "21",
            "new_relic_data_schema_version": 2,
        },
    ),
]


@reset_core_stats_engine()
def test_numpy_str_array_multiple_features():
    @validate_ml_events(numpy_str_recorded_custom_events)
    @validate_ml_event_count(count=2)
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
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "DecisionTreeClassifier",
            "model_version": "0.0.0",
            "new_relic_data_schema_version": 2,
        },
    )
]


disabled_inference_value_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": False,
    "ml_insights_events.enabled": True,
}


@override_application_settings(disabled_inference_value_settings)
@reset_core_stats_engine()
def test_does_not_include_value_when_inference_event_value_enabled_is_false():
    @validate_ml_events(numpy_str_recorded_custom_events_no_value)
    @validate_ml_event_count(count=1)
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


disabled_ml_insights_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": False,
}


@override_application_settings(disabled_ml_insights_settings)
@reset_core_stats_engine()
def test_does_not_include_events_when_ml_insights_events_enabled_is_false():
    """
    Verifies that all ml events can be disabled by setting
    custom_insights_events.enabled.
    """

    @validate_ml_event_count(count=0)
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


disabled_ml_settings = {
    "machine_learning.enabled": False,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": True,
}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
def test_does_not_include_events_when_machine_learning_enabled_is_false():
    @validate_ml_event_count(count=0)
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


multilabel_output_label_events = [
    (
        {"type": "InferenceData"},
        {
            "inference_id": None,
            "prediction_id": None,
            "modelName": "MultiOutputClassifier",
            "model_version": "0.0.0",
            "label.0": "1",
            "label.1": "0",
            "label.2": "1",
            "feature.0": 3.0,
            "feature.1": 5.0,
            "feature.2": 3.0,
            "feature.3": 0.0,
            "feature.4": 0.0,
            "feature.5": 2.0,
            "feature.6": 2.0,
            "feature.7": 0.0,
            "feature.8": 4.0,
            "feature.9": 3.0,
            "feature.10": 2.0,
            "feature.11": 5.0,
            "feature.12": 2.0,
            "feature.13": 3.0,
            "feature.14": 3.0,
            "feature.15": 4.0,
            "feature.16": 3.0,
            "feature.17": 1.0,
            "feature.18": 2.0,
            "feature.19": 4.0,
            "new_relic_data_schema_version": 2,
        },
    )
]


@reset_core_stats_engine()
def test_custom_event_count_multilabel_output():
    @validate_ml_events(multilabel_output_label_events)
    @validate_ml_event_count(count=1)
    @background_task()
    def _test():
        from sklearn.datasets import make_multilabel_classification
        from sklearn.linear_model import LogisticRegression
        from sklearn.multioutput import MultiOutputClassifier

        x_train, y_train = make_multilabel_classification(n_classes=3, random_state=0)
        clf = MultiOutputClassifier(LogisticRegression()).fit(x_train, y_train)
        clf.predict([x_train[-1]])

    _test()
