def instrument_psycopg2_extensions(module):

    _register_type = module.register_type

    def _register_type_wrapper(type, obj=None):
        if obj is not None:
            if hasattr(obj, '_nr_cursor'):
                obj = obj._nr_cursor
            elif hasattr(obj, '_nr_connection'):
                obj = obj._nr_connection
            return _register_type(type, obj)
        else:
            return _register_type(type)

    module.register_type = _register_type_wrapper
