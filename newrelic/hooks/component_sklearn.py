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
import uuid
import numpy as np
from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction
from newrelic.core.config import global_settings
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper


def wrap_method(wrapped, instance, args, kwargs):
    # If there is no transaction, do not wrap anything.
    if not current_transaction():
        return wrapped(*args, **kwargs)

    method_name = wrapped.__name__

    # If the method has already been wrapped do not wrap it again. This happens
    # when one model inherits from another and they both implement the method.
    if getattr(instance, "_nr_wrapped_%s" % method_name, False):
        return wrapped(*args, **kwargs)

    # Set the _nr_wrapped attribute to denote that this method is being wrapped.
    setattr(instance, "_nr_wrapped_%s" % method_name, True)

    # MLModel/Sklearn/Named/<class name>.<method name>
    func_name = wrapped.__name__
    model_name = wrapped.__self__.__class__.__name__
    name = "%s.%s" % (model_name, func_name)
    with FunctionTrace(name=name, group="MLModel/Sklearn/Named", source=wrapped):
        return_val = wrapped(*args, **kwargs)

    # Set the _nr_wrapped attribute to denote that this method is no longer wrapped.
    setattr(instance, "_nr_wrapped_%s" % method_name, False)

    return return_val


def bind_predict(x, check_input=True):
    return x, check_input


def wrap_predict(wrapped, instance, args, kwargs):
    data_set, check_input = bind_predict(*args, **kwargs)
    inference_id = uuid.uuid4()
    model_name = instance.__class__.__name__

    #transaction = current_transaction()

    #if transaction:
    #    settings = transaction.settings
    #else:
    #    settings = global_settings()

    #if settings and settings.machine_learning and settings.machine_learning.inference_event_value.enabled:
     #   if transaction:
     #       transaction.record_custom_event("ML Model Feature Event", {"inference_id": inference_id, "model_name": model_name,})
     #   else:
     #       application = application_instance(activate=False)
     #       if application and application.enabled:
     #           transaction.record_custom_event("ML Model Feature Event", {"inference_id": inference_id, "model_name": model_name, })

    return wrapped(*args, **kwargs)


def _nr_instrument_model(module, model_class):
    methods_to_wrap = ("predict", "fit", "fit_predict", "predict_log_proba", "predict_proba", "transform", "score")
    for method_name in methods_to_wrap:
        if hasattr(getattr(module, model_class), method_name):
            wrap_function_wrapper(module, "%s.%s" % (model_class, method_name), wrap_method)


def instrument_sklearn_tree_models(module):
    if hasattr(module.BaseDecisionTree, "predict"):
        wrap_function_wrapper(module, "BaseDecisionTree.predict", wrap_predict)

    model_classes = (
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    )
    for model_cls in model_classes:
        if hasattr(module, model_cls):
            _nr_instrument_model(module, model_cls)

