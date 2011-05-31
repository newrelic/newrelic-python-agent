import sys
import types

from newrelic.agent import (wrap_name_transaction, wrap_function_trace,
                            wrap_error_trace, wrap_object, callable_name,
                            transaction, import_module)

class capture_error(object):
    def __init__(self, wrapped):
        self.__wrapped__ = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, controller, func, args):
        current_transaction = transaction()
        if current_transaction:
            webob_exc = import_module('webob.exc')
            try:
                return self.__wrapped__(controller, func, args)
            except webob_exc.HTTPException:
                raise
            except:
                current_transaction.notice_error(*sys.exc_info())
                raise
        else:
            return self.__wrapped__(controller, func, args)

def instrument(module):

    if module.__name__ == 'pylons.wsgiapp':
        wrap_error_trace(module, 'PylonsApp.__call__')

    elif module.__name__ == 'pylons.controllers.core':
        wrap_name_transaction(module, 'WSGIController.__call__',
                              (lambda self, environ, start_response:
                              callable_name(self)), 'Pylons')
        wrap_function_trace(module, 'WSGIController.__call__')
        wrap_function_trace(module, 'WSGIController._perform_call',
                            (lambda self, func, args: callable_name(func)))
        wrap_object(module, 'WSGIController._perform_call', capture_error)

    elif module.__name__ == 'pylons.templating':

        wrap_function_trace(module, 'render_genshi')
        wrap_function_trace(module, 'render_mako')
        wrap_function_trace(module, 'render_jinja2')
