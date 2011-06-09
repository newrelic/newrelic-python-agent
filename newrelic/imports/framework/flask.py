import sys

from newrelic.agent import (FunctionTraceWrapper, wrap_in_function,
        wrap_pre_function, wrap_function_trace, transaction,
        NameTransactionWrapper)

def wrap_add_url_rule_input(self, rule, endpoint=None, view_func=None,
        **options):
    if view_func is not None:
        view_func = NameTransactionWrapper(view_func, None, 'Flask')
        view_func = FunctionTraceWrapper(view_func)
    return ((self, rule, endpoint, view_func), options)

def wrap_handle_exception(self, e):
    current_transaction = transaction()
    if current_transaction:
        current_transaction.notice_error(*sys.exc_info())

def instrument(module):

    if module.__name__ == 'flask.app':
        wrap_in_function(module, 'Flask.add_url_rule',
            wrap_add_url_rule_input)
        wrap_pre_function(module, 'Flask.handle_exception',
            wrap_handle_exception)

    elif module.__name__ == 'flask':
        wrap_function_trace(module, 'render_template')
        wrap_function_trace(module, 'render_template_string')
