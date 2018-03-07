from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_database_node(validator):

    # Accepts one argument, a function that itself takes one argument: the
    # node. The validator should raise an exception if the node is not correct.

    nodes = []

    @transient_function_wrapper('newrelic.core.database_node',
            'DatabaseNode.__new__')
    def _validate_explain_plan(wrapped, instance, args, kwargs):
        node = wrapped(*args, **kwargs)
        nodes.append(node)
        return node

    @function_wrapper
    def _validate(wrapped, instance, args, kwargs):
        new_wrapper = _validate_explain_plan(wrapped)
        result = new_wrapper(*args, **kwargs)

        for node in nodes:
            validator(node)

        return result

    return _validate
