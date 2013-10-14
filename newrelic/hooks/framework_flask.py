import sys

import newrelic.api.transaction
import newrelic.api.function_trace
import newrelic.api.in_function
import newrelic.api.pre_function
import newrelic.api.transaction_name
import newrelic.api.web_transaction

def wrap_add_url_rule_input(app, rule, endpoint=None, view_func=None,
        **options):
    if view_func is not None:
        view_func = newrelic.api.transaction_name.TransactionNameWrapper(view_func)
        view_func = newrelic.api.function_trace.FunctionTraceWrapper(view_func)
    return ((app, rule, endpoint, view_func), options)

def wrap_handle_exception(self, e):
    current_transaction = newrelic.api.transaction.current_transaction()
    if current_transaction:
        current_transaction.record_exception(*sys.exc_info())

def instrument(module):

    if module.__name__ == 'flask.app':
        newrelic.api.web_transaction.wrap_wsgi_application(
                module, 'Flask.wsgi_app')
        newrelic.api.in_function.wrap_in_function(
                module, 'Flask.add_url_rule', wrap_add_url_rule_input)
        newrelic.api.pre_function.wrap_pre_function(
                module, 'Flask.handle_exception', wrap_handle_exception)

    elif module.__name__ == 'flask.templating':
        newrelic.api.function_trace.wrap_function_trace(
                module, 'render_template')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'render_template_string')
