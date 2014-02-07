"""Instrumentation module for Flask framework.

"""

from newrelic.agent import (current_transaction, wrap_wsgi_application,
    wrap_function_wrapper,  callable_name, wrap_function_trace,
    FunctionTrace, TransactionNameWrapper, function_wrapper,
    ignore_status_code)

def framework_details():
    import flask
    return ('Flask', getattr(flask, '__version__', None))

def should_ignore(exc, value, tb):
    from werkzeug.exceptions import HTTPException

    # Werkzeug HTTPException can be raised internally by Flask or in
    # user code if they mix Flask with Werkzeug. Filter based on the
    # HTTP status code.

    if isinstance(value, HTTPException):
        if ignore_status_code(value.code):
            return True

@function_wrapper
def handler_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)

    # Set priority=2 so this will take precedence over any error
    # handler which will be at priority=1.

    transaction.set_transaction_name(name, priority=2)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

def wrapper_Flask_add_url_rule_input(wrapped, instance, args, kwargs):
    def _bind_params(rule, endpoint=None, view_func=None, **options):
        return rule, endpoint, view_func, options

    rule, endpoint, view_func, options = _bind_params(*args, **kwargs)

    if view_func is not None:
        view_func = handler_wrapper(view_func)

    return wrapped(rule, endpoint, view_func, **options)

def wrapper_Flask_handle_http_exception(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)

    # Because we use priority=1, this name will only be used in cases
    # where an error handler was called without an actual request
    # handler having already being called.

    transaction.set_transaction_name(name, priority=1)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

def wrapper_Flask_handle_exception(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    # The Flask.handle_exception() method is always called in the
    # context of the except clause of the try block. We can therefore
    # rely on grabbing current exception details so we have access to
    # the addition stack trace information.

    transaction.record_exception(ignore_errors=should_ignore)

    name = callable_name(wrapped)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

@function_wrapper
def error_handler_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)

    # Because we use priority=1, this name will only be used in cases
    # where an error handler was called without an actual request
    # handler having already being called.

    transaction.set_transaction_name(name, priority=1)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

def wrapper_Flask__register_error_handler(wrapped, instance, args, kwargs):
    def _bind_params(key, code_or_exception, f):
        return key, code_or_exception, f

    key, code_or_exception, f = _bind_params(*args, **kwargs)

    f = error_handler_wrapper(f)

    return wrapped(key, code_or_exception, f)

def instrument_flask_app(module):
    wrap_wsgi_application(module, 'Flask.wsgi_app',
            framework=framework_details())

    wrap_function_wrapper(module, 'Flask.add_url_rule',
            wrapper_Flask_add_url_rule_input)

    wrap_function_wrapper(module, 'Flask.handle_http_exception',
            wrapper_Flask_handle_http_exception)

    # Use the same wrapper for initial user exception processing and
    # fallback for unhandled exceptions.

    if hasattr(module.Flask, 'handle_user_exception'):
        wrap_function_wrapper(module, 'Flask.handle_user_exception',
                wrapper_Flask_handle_exception)

    wrap_function_wrapper(module, 'Flask.handle_exception',
            wrapper_Flask_handle_exception)

    # The _register_error_handler() method was only introduced in
    # Flask version 0.7.0.

    if hasattr(module.Flask, '_register_error_handler'):
        wrap_function_wrapper(module, 'Flask._register_error_handler',
                wrapper_Flask__register_error_handler)

def instrument_flask_templating(module):
    wrap_function_trace(module, 'render_template')
    wrap_function_trace(module, 'render_template_string')
