from newrelic.api.function_trace import (
    FunctionTrace,
    FunctionTraceWrapper,
    wrap_function_trace,
)
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper

# def _nr_wrapper_sklearn_base_decision_tree_predict(wrapped, instance, args, kwargs):
#     transaction = current_transaction()
#
#     if transaction is None:
#         return wrapped(*args, **kwargs)
#
#     name = getattr(wrapped, "", "sklearn.tree.DecisionTreeClassifier:predict")
#
#     with FunctionTrace(name=name):
#         return wrapped(*args, **kwargs)


def instrument_sklearn_tree(module):
    if module.__name__ == 'sklearn.tree':
        if hasattr(module.DecisionTreeClassifier, "predict"):
            wrap_function_trace(module, "DecisionTreeClassifier.predict")

        if hasattr(module.DecisionTreeRegressor, "predict"):
            wrap_function_trace(module, "DecisionTreeRegressor.predict")

        if hasattr(module.ExtraTreeRegressor, "predict"):
            wrap_function_trace(module, "ExtraTreeRegressor.predict")

        if hasattr(module.ExtraTreeRegressor, "predict"):
            wrap_function_trace(module, "ExtraTreeClassifier.predict")

        # wrap_function_trace(module, "BaseDecisionTree.predict")
        # wrap_function_wrapper(
        #     module,
        #     "BaseDecisionTree.predict",
        #     _nr_wrapper_sklearn_base_decision_tree_predict
        # )
