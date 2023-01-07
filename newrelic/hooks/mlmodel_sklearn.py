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

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
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
            return PredictReturnTypeProxy(return_val, model_name=_class, training_step=training_step)
        return return_val

    wrap_function_wrapper(module, "%s.%s" % (_class, method), _nr_wrapper_method)


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


def instrument_sklearn_naive_bayes_models(module):
    model_classes = (
        "GaussianNB",
        "MultinomialNB",
        "ComplementNB",
        "BernoulliNB",
        "CategoricalNB",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_model_selection_models(module):
    model_classes = (
        "GridSearchCV",
        "RandomizedSearchCV",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_mixture_models(module):
    model_classes = (
        "GaussianMixture",
        "BayesianGaussianMixture",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_neural_network_models(module):
    model_classes = (
        "BernoulliRBM",
        "MLPClassifier",
        "MLPRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_neighbors_KRadius_models(module):
    model_classes = (
        "KNeighborsClassifier",
        "RadiusNeighborsClassifier",
        "KNeighborsTransformer",
        "RadiusNeighborsTransformer",
        "KNeighborsRegressor",
        "RadiusNeighborsRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_svm_models(module):
    model_classes = (
        "LinearSVC",
        "LinearSVR",
        "SVC",
        "NuSVC",
        "SVR",
        "NuSVR",
        "OneClassSVM",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_semi_supervised_models(module):
    model_classes = (
        "LabelPropagation",
        "LabelSpreading",
        "SelfTrainingClassifier",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_pipeline_models(module):
    model_classes = (
        "Pipeline",
        "FeatureUnion",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_neighbors_models(module):
    model_classes = (
        "KernelDensity",
        "LocalOutlierFactor",
        "NeighborhoodComponentsAnalysis",
        "NearestCentroid",
        "NearestNeighbors",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_metrics(module):
    for scorer in METRIC_SCORERS:
        if hasattr(module, scorer):
            wrap_function_wrapper(module, scorer, wrap_metric_scorer)
