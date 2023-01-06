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
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction
from newrelic.core.config import global_settings
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper

METHODS_TO_WRAP = ("predict", "fit", "fit_predict", "predict_log_proba", "predict_proba", "transform", "score")
METRIC_SCORERS = (
    "accuracy_score",
    "balanced_accuracy_score",
    "f1_score",
    "precision_score",
    "recall_score",
    "roc_auc_score",
    "r2_score",
)
PY2 = sys.version_info[0] == 2


class PredictReturnTypeProxy(ObjectProxy):
    def __init__(self, wrapped, model_name, training_step):
        super(ObjectProxy, self).__init__(wrapped)
        self._nr_model_name = model_name
        self._nr_training_step = training_step


def _wrap_method_trace(module, _class, method, name=None, group=None):
    def _nr_wrapper_method(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        trace = current_trace()

        if transaction is None:
            return wrapped(*args, **kwargs)

        wrapped_attr_name = "_nr_wrapped_%s" % method

        # If the method has already been wrapped do not wrap it again. This happens
        # when one class inherits from another and they both implement the method.
        if getattr(trace, wrapped_attr_name, False):
            return wrapped(*args, **kwargs)

        trace = FunctionTrace(name=name, group=group, source=wrapped)

        try:
            # Set the _nr_wrapped attribute to denote that this method is being wrapped.
            setattr(trace, wrapped_attr_name, True)

            with trace:
                return_val = wrapped(*args, **kwargs)
        finally:
            # Set the _nr_wrapped attribute to denote that this method is no longer wrapped.
            setattr(trace, wrapped_attr_name, False)

        # If this is the fit method, increment the training_step counter.
        if method in ("fit", "fit_predict"):
            training_step = getattr(instance, "_nr_wrapped_training_step", -1)
            setattr(instance, "_nr_wrapped_training_step", training_step + 1)

        # If this is the predict method, wrap the return type in an nr type with
        # _nr_wrapped attrs that will attach model info to the data.
        if method in ("predict", "fit_predict"):
            training_step = getattr(instance, "_nr_wrapped_training_step", "Unknown")
            wrap_predict(transaction, _class, wrapped, instance, args, kwargs)
            return PredictReturnTypeProxy(return_val, model_name=_class, training_step=training_step)
        return return_val

    wrap_function_wrapper(module, "%s.%s" % (_class, method), _nr_wrapper_method)


def find_type_category(value):
    value_type = None
    python_type = str(type(value))
    if "int" in python_type or "float" in python_type or "complex" in python_type:
        value_type = "numerical"
    elif "bool" in python_type:
        value_type = "bool"
    elif "str" in python_type or "unicode" in python_type:
        value_type = "str"
    return value_type


def bind_predict(X, *args, **kwargs):
    return X


def wrap_predict(transaction, _class, wrapped, instance, args, kwargs):
    data_set = bind_predict(*args, **kwargs)
    inference_id = uuid.uuid4()
    model_name = getattr(instance, "_nr_wrapped_name", _class)
    model_version = getattr(instance, "_nr_wrapped_version", "0.0.0")

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if settings and settings.machine_learning and settings.machine_learning.inference_event_value.enabled:
        #Pandas Dataframe
        pd = sys.modules.get("pandas", None)
        if pd and isinstance(data_set, pd.DataFrame):
            for (colname, colval) in data_set.iteritems():
                for value in colval.values:
                    value_type = data_set[colname].dtype.name
                    if value_type == "category":
                        value_type = "categorical"
                    else:
                        value_type = find_type_category(value)
                    transaction.record_custom_event("ML Model Feature Event",
                                                    {"inference_id": inference_id, "model_name": model_name,
                                                     "model_version": model_version, "feature_name": colname,
                                                     "type": value_type, "value": str(value),})
        else:
            for feature in data_set:
                for col_index, value in enumerate(feature):
                    transaction.record_custom_event("ML Model Feature Event",
                                                    {"inference_id": inference_id, "model_name": model_name,
                                                     "model_version": model_version, "feature_name": str(col_index),
                                                     "type": find_type_category(value), "value": str(value),})


def _nr_instrument_model(module, model_class):
    for method_name in METHODS_TO_WRAP:
        if hasattr(getattr(module, model_class), method_name):
            # Function/MLModel/Sklearn/Named/<class name>.<method name>
            name = "MLModel/Sklearn/Named/%s.%s" % (model_class, method_name)
            _wrap_method_trace(module, model_class, method_name, name=name)


def _instrument_sklearn_models(module, model_classes):
    for model_cls in model_classes:
        if hasattr(module, model_cls):
            _nr_instrument_model(module, model_cls)


def _bind_scorer(y_true, y_pred, *args, **kwargs):
    return y_true, y_pred, args, kwargs


def wrap_metric_scorer(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    # If there is no transaction, do not wrap anything.
    if not transaction:
        return wrapped(*args, **kwargs)

    score = wrapped(*args, **kwargs)

    y_true, y_pred, args, kwargs = _bind_scorer(*args, **kwargs)
    model_name = "Unknown"
    training_step = "Unknown"
    if hasattr(y_pred, "_nr_model_name"):
        model_name = y_pred._nr_model_name
    if hasattr(y_pred, "_nr_training_step"):
        training_step = y_pred._nr_training_step
    # Attribute values must be int, float, str, or boolean. If it's not one of these
    # types and an iterable add the values as separate attributes.
    if not isinstance(score, (str, int, float, bool)):
        if hasattr(score, "__iter__"):
            for i, s in enumerate(score):
                transaction._add_agent_attribute(
                    "%s/TrainingStep/%s/%s[%s]" % (model_name, training_step, wrapped.__name__, i), s
                )
    else:
        transaction._add_agent_attribute("%s/TrainingStep/%s/%s" % (model_name, training_step, wrapped.__name__), score)
    return score


def instrument_sklearn_tree_models(module):
    model_classes = (
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_bagging_models(module):
    model_classes = (
        "BaggingClassifier",
        "BaggingRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_forest_models(module):
    model_classes = (
        "ExtraTreesClassifier",
        "ExtraTreesRegressor",
        "RandomForestClassifier",
        "RandomForestRegressor",
        "RandomTreesEmbedding",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_iforest_models(module):
    model_classes = ("IsolationForest",)
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_weight_boosting_models(module):
    model_classes = (
        "AdaBoostClassifier",
        "AdaBoostRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_gradient_boosting_models(module):
    model_classes = (
        "GradientBoostingClassifier",
        "GradientBoostingRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_voting_models(module):
    model_classes = (
        "VotingClassifier",
        "VotingRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_stacking_models(module):
    module_classes = (
        "StackingClassifier",
        "StackingRegressor",
    )
    _instrument_sklearn_models(module, module_classes)


def instrument_sklearn_ensemble_hist_models(module):
    model_classes = (
        "HistGradientBoostingClassifier",
        "HistGradientBoostingRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_calibration_models(module):
    model_classes = ("CalibratedClassifierCV",)
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_cluster_models(module):
    model_classes = (
        "AffinityPropagation",
        "Birch",
        "DBSCAN",
        "MeanShift",
        "OPTICS",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_cluster_agglomerative_models(module):
    model_classes = (
        "AgglomerativeClustering",
        "FeatureAgglomeration",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_cluster_clustering_models(module):
    model_classes = (
        "SpectralBiclustering",
        "SpectralCoclustering",
        "SpectralClustering",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_cluster_kmeans_models(module):
    model_classes = (
        "BisectingKMeans",
        "KMeans",
        "MiniBatchKMeans",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_metrics(module):
    for scorer in METRIC_SCORERS:
        if hasattr(module, scorer):
            wrap_function_wrapper(module, scorer, wrap_metric_scorer)
