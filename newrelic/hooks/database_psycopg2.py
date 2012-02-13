def instrument_psycopg2_extensions(module):

    _register_type = module.register_type

    def _register_type_wrapper(obj, scope=None):
        if hasattr(scope, '_nr_cursor'):
            scope = scope._nr_cursor
        elif hasattr(scope, '_nr_connection'):
            scope = scope._nr_connection
        return _register_type(obj, scope)

    module.register_type = _register_type_wrapper
