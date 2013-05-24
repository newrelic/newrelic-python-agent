from __future__ import with_statement

from newrelic.agent import (callable_name, current_transaction,
        wrap_callable, wrap_out_function, wrap_wsgi_application,
        ErrorTrace, FunctionTrace)

def instrument_pyramid_router(module):
    pyramid_version = None

    try:
        import pkg_resources
        pyramid_version = pkg_resources.get_distribution('pyramid').version
    except Exception:
        pass

    wrap_wsgi_application(module, 'Router.__call__',
            framework=('Pyramid', pyramid_version))

def view_handler_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    try:
        view_callable = wrapped.__original_view__ or wrapped
    except AttributeError:
        view_callable = wrapped

    name = callable_name(view_callable)

    transaction.set_transaction_name(name)

    with FunctionTrace(transaction, name):
        with ErrorTrace(transaction, ignore_errors=[
                'pyramid.httpexceptions:HTTPNotFound']):
            return wrapped(*args, **kwargs)

def wrap_view_handler(mapped_view):
    return wrap_callable(mapped_view, view_handler_wrapper)

def instrument_pyramid_config_views(module):
    # Location of the ViewDeriver class changed from pyramid.config to
    # pyramid.config.views so check if present before trying to update.

    if hasattr(module, 'ViewDeriver'):
        wrap_out_function(module, 'ViewDeriver.mapped_view',
                wrap_view_handler)
