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

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

METHODS_TO_WRAP = ("predict", "fit", "fit_predict", "predict_log_proba", "predict_proba", "transform", "score")


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


def instrument_sklearn_tree_models(module):
    model_classes = (
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_ensemble_models(module):
    model_classes = (
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
    _instrument_sklearn_models(module, model_classes)
