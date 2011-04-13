import sys

from newrelic.agent import (FunctionTraceWrapper, wrap_in_function,
        wrap_pre_function, wrap_function_trace, transaction)

def wrap_add_url_rule_input(self, rule, endpoint=None, view_func=None,
        **options):
    if view_func is not None:
        view_func = FunctionTraceWrapper(view_func, override_path=True)
    return ((self, rule, endpoint, view_func), options)

def wrap_handle_exception(self, e):
    current_transaction = transaction()
    if current_transaction:
        current_transaction.runtime_error(*sys.exc_info())

def name_render_template(template_name, **context):
    return '%s Template' % template_name

def instrument(module):

    wrap_in_function('flask.app', 'Flask', 'add_url_rule',
        wrap_add_url_rule_input)

    wrap_pre_function('flask.app', 'Flask', 'handle_exception',
        wrap_handle_exception)

    wrap_function_trace('flask', None, 'render_template')
    wrap_function_trace('flask', None, 'render_template_string')
