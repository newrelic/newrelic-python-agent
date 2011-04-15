import sys

from newrelic.agent import (wrap_function_trace, wrap_object, transaction,
         wrap_error_trace, wrap_out_function)

def name_models(environment):
    return '%s/%s Models' % (environment['request'].controller,
            environment['request'].function)

def name_controller(controller, function, environment):
    return '%s/%s Controller' % (controller, function)

def name_view(environment):
    return '%s/%s View' % (environment['request'].controller,
            environment['request'].function)

def name_restricted(code, environment={}, layer='Unknown'):
    folder = environment['request'].folder
    if layer.startswith(folder):
        return '%s Execute' % layer[len(folder):]
    return '%s Execute' % layer

class name_transaction(object):
    def __init__(self, wrapped):
        self._wrapped = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, environment):
        current_transaction = transaction()
        if current_transaction:
            current_transaction.path = environment['response'].view
        return self._wrapped(environment)

class runtime_error(object):
    def __init__(self, wrapped):
        self._wrapped = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, request, response, session):
        current_transaction = transaction()
        if current_transaction:
            from gluon.http import HTTP
            try:
                return self._wrapped(request, response, session)
            except HTTP:
                raise
            except:
                current_transaction.runtime_error(*sys.exc_info())
                raise
        else:
            return self._wrapped(request, response, session)

def instrument(module):

    if module.__name__ == 'gluon.compileapp':
        wrap_function_trace(module, None, 'run_models_in',
                name_models)
        wrap_function_trace(module, None, 'run_controller_in',
                name_controller)
        wrap_function_trace(module, None, 'run_view_in',
                name_view)

        wrap_function_trace(module, None, 'restricted',
                name_restricted)

        wrap_object(module, None, 'run_models_in', name_transaction)

    elif module.__name__ == 'gluon.main':
        wrap_object(module, None, 'serve_controller', runtime_error)
