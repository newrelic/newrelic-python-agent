from newrelic.api.function_trace import (
    FunctionTrace,
    FunctionTraceWrapper,
    wrap_function_trace,
)
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper


def _nr_wrapper_sklearn_base_decision_tree_predict(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    with FunctionTrace(name="DecisionTreeClassifier.Predict", group="ML"):
        return wrapped(*args, **kwargs)


def instrument_sklearn_tree(module):
    if module.__name__ == 'sklearn.tree':

        wrap_function_wrapper(
            module,
            "BaseDecisionTree.predict",
            _nr_wrapper_sklearn_base_decision_tree_predict
        )
