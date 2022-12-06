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
from newrelic.common.object_wrapper import wrap_function_wrapper

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


def _wrap_predict_return_type(data, model_name):
    """
    Returns a new NR custom type with model info attached to it as attrs.
    """
    import numpy as np

    try:
        # Numpy NDArrays require special implementation to subclass.
        if isinstance(data, np.ndarray):

            class NRNumpyNDArray(np.ndarray):
                _nr_wrapped_model_name = model_name

                def __array_wrap__(self, obj):
                    if obj.shape == ():
                        return obj[()]  # if ufunc output is scalar, return it
                    else:
                        return np.ndarray.__array_wrap__(self, obj)

            return data.view(NRNumpyNDArray)

        # Booleans are singletons and require special implementation to subclass.
        if isinstance(data, (bool)):
            if PY2:
                class NRBoolType:
                    _nr_wrapped_model_name = model_name

                    def __init__(self, value):
                        self.value = value

                    def __nonzero__(self):
                        return bool(self.value)

            else:

                class NRBoolType:
                    _nr_wrapped_model_name = model_name

                    def __init__(self, value):
                        self.value = value

                    def __bool__(self):
                        return bool(self.value)

            return NRBoolType(data)

        # Attempt to subclass the type directly.
        class NRWrapType(type(data)):
            _nr_wrapped_model_name = model_name

        return NRWrapType(data)
    except:  # Squash any exceptions resulting from attempted wrap typing.
        pass
    return data


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

        # If this is the predict method, wrap the return type in an nr type with
        # _nr_wrapped attrs that will attach model info to the data.
        if method == "predict":
            return _wrap_predict_return_type(return_val, model_name=_class)
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
    if hasattr(y_pred, "_nr_wrapped_model_name"):
        model_name = y_pred._nr_wrapped_model_name
    # Attribute values must be int, float, str, or boolean. If it's not one of these
    # types and an iterable add the values as separate attributes.
    if not isinstance(score, (str, int, float, bool)):
        if hasattr(score, "__iter__"):
            for i, s in enumerate(score):
                transaction._add_agent_attribute("%s.%s[%s]" % (model_name, wrapped.__name__, i), s)
    else:
        transaction._add_agent_attribute("%s.%s" % (model_name, wrapped.__name__), score)
    return score


def instrument_sklearn_tree_models(module):
    model_classes = (
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    )
    _instrument_sklearn_models(module, model_classes)


def instrument_sklearn_metrics(module):
    for scorer in METRIC_SCORERS:
        if hasattr(module, scorer):
            wrap_function_wrapper(module, scorer, wrap_metric_scorer)
