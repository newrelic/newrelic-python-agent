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

from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper


def wrap_model_method(method_name):
    @function_wrapper
    def _wrap_method(wrapped, instance, args, kwargs):
        # If there is no transaction, do not wrap anything.
        if not current_transaction():
            return wrapped(*args, **kwargs)

        # If the method has already been wrapped do not wrap it again. This happens
        # when one model inherits from another and they both implement the method.
        if getattr(instance, "_nr_wrapped_%s" % method_name, False):
            return wrapped(*args, **kwargs)

        # Set the _nr_wrapped attribute to denote that this method is being wrapped.
        setattr(instance, "_nr_wrapped_%s" % method_name, True)

        # MLModel/Sklearn/Named/<class name>.<method name>
        func_name = wrapped.__name__
        name = "%s.%s" % (wrapped.__self__.__class__.__name__, func_name)
        return_val = FunctionTraceWrapper(wrapped, name=name, group="MLModel/Sklearn/Named")(*args, **kwargs)

        # Set the _nr_wrapped attribute to denote that this method is no longer wrapped.
        setattr(instance, "_nr_wrapped_%s" % method_name, False)

        return return_val

    return _wrap_method


def wrap_model_init(wrapped, instance, args, kwargs):
    return_val = wrapped(*args, **kwargs)

    methods_to_wrap = ("predict", "fit", "fit_predict", "predict_log_proba", "predict_proba", "transform", "score")
    for method_name in methods_to_wrap:
        if hasattr(instance, method_name):
            setattr(instance, method_name, wrap_model_method(method_name)(getattr(instance, method_name)))

    return return_val


def instrument_sklearn_models(module):
    tree_model_classes = (
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    )
    ensemble_model_classes = (
        "AdaBoostClassifier",
        "AdaBoostRegressor",
        "BaggingClassifier",
        "BaggingRegressor",
        "ExtraTreesClassifier",
        "ExtraTreesRegressor",
        "GradientBoostingClassifier",
        "GradientBoostingRegressor",
        "HistGradientBoostingClassifier",
        "HistGradientBoostingRegressor",
        "IsolationForest",
        "RandomForestClassifier",
        "RandomForestRegressor",
        "StackingClassifier",
        "StackingRegressor",
        "VotingClassifier",
        "VotingRegressor",
    )
    linear_model_classes = (
        "ARDRegression",
        "BayesianRidge",
        "ElasticNet",
        "ElasticNetCV",
        "Hinge",
        "Huber",
        "HuberRegressor",
        "Lars",
        "LarsCV",
        "Lasso",
        "LassoCV",
        "LassoLars",
        "LassoLarsCV",
        "LassoLarsIC",
        "LinearRegression",
        "Log",
        "LogisticRegression",
        "LogisticRegressionCV",
        "ModifiedHuber",
        "MultiTaskElasticNet",
        "MultiTaskElasticNetCV",
        "MultiTaskLasso",
        "MultiTaskLassoCV",
        "OrthogonalMatchingPursuit",
        "OrthogonalMatchingPursuitCV",
        "PassiveAggressiveClassifier",
        "PassiveAggressiveRegressor",
        "Perceptron",
        "QuantileRegressor",
        "Ridge",
        "RidgeCV",
        "RidgeClassifier",
        "RidgeClassifierCV",
        "SGDClassifier",
        "SGDRegressor",
        "SGDOneClassSVM",
        "SquaredLoss",
        "TheilSenRegressor",
        "RANSACRegressor",
        "PoissonRegressor",
        "GammaRegressor",
        "TweedieRegressor",
    )
    for model_class in tree_model_classes:
        if hasattr(module, model_class):
            wrap_function_wrapper(module, "%s.%s" % (model_class, "__init__"), wrap_model_init)
    for model_class in ensemble_model_classes:
        if hasattr(module, model_class):
            wrap_function_wrapper(module, "%s.%s" % (model_class, "__init__"), wrap_model_init)
    for model_class in linear_model_classes:
        if hasattr(module, model_class):
            wrap_function_wrapper(module, "%s.%s" % (model_class, "__init__"), wrap_model_init)
