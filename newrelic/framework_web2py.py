import sys

from newrelic.agent import (wrap_function_trace, wrap_object, transaction,
         wrap_error_trace, wrap_out_function, wrap_name_transaction)

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

class capture_error(object):
    def __init__(self, wrapped):
        self.__wrapped__ = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, request, response, session):
        current_transaction = transaction()
        if current_transaction:
            from gluon.http import HTTP
            try:
                return self.__wrapped__(request, response, session)
            except HTTP:
                raise
            except:
                current_transaction.notice_error(*sys.exc_info())
                raise
        else:
            return self.__wrapped__(request, response, session)

def instrument(module):

    if module.__name__ == 'gluon.compileapp':
        wrap_function_trace(module, 'run_models_in', name_models)
        wrap_function_trace(module, 'run_controller_in', name_controller)
        wrap_function_trace(module, 'run_view_in', name_view)

        wrap_function_trace(module, 'restricted', name_restricted)

        wrap_name_transaction(module, 'run_models_in',
                lambda environment: environment['response'].view)

    elif module.__name__ == 'gluon.main':
        wrap_object(module, 'serve_controller', capture_error)
