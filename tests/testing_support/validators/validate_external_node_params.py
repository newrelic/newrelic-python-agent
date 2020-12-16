from newrelic.common.object_wrapper import transient_function_wrapper


def validate_external_node_params(params=[], forgone_params=[]):
    """
    Validate the parameters on the external node.

    params: a list of tuples
    forgone_params: a flat list
    """
    @transient_function_wrapper('newrelic.api.external_trace',
            'ExternalTrace.process_response_headers')
    def _validate_external_node_params(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # This is only validating that logic to extract cross process
        # header and update params in ExternalTrace is succeeding. This
        # is actually done after the ExternalTrace __exit__() is called
        # with the ExternalNode only being updated by virtue of the
        # original params dictionary being aliased rather than copied.
        # So isn't strictly validating that params ended up in the actual
        # ExternalNode in the transaction trace.

        for name, value in params:
            assert instance.params[name] == value

        for name in forgone_params:
            assert name not in instance.params

        return result

    return _validate_external_node_params
