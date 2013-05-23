from __future__ import with_statement

from newrelic.api.out_function import wrap_out_function
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.error_trace import ErrorTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wrap_wsgi_application
from newrelic.api.object_wrapper import ObjectWrapper, callable_name

def instrument_pyramid_router(module):

    pyramid_version = None

    try:
        import pkg_resources
        pyramid_version = pkg_resources.get_distribution('pyramid').version

    except Exception:
        pass

    wrap_wsgi_application(module, 'Router.__call__',
            framework=('Pyramid', pyramid_version))

def instrument_pyramid_config_views(module):

    # Location of the ViewDeriver class changed from pyramid.config to
    # pyramid.config.views so check if present before trying to update.

    def wrap_mapped_view(mapped_view):
        def wrapper(wrapped, instance, args, kwargs):
            transaction = current_transaction()

            if not transaction:
                return wrapped(*args, **kwargs)

            view_callable = wrapped
            if hasattr(view_callable, '__original_view__'):
                original_view = view_callable.__original_view__
                if original_view:
                    view_callable = original_view

            name = callable_name(view_callable)

            transaction.name_transaction(name)

            with FunctionTrace(transaction, name):
                with ErrorTrace(transaction, ignore_errors=[
                        'pyramid.httpexceptions:HTTPNotFound']):
                    return wrapped(*args, **kwargs)

        return ObjectWrapper(mapped_view, None, wrapper)

    if hasattr(module, 'ViewDeriver'):
        wrap_out_function(module, 'ViewDeriver.mapped_view',
                wrap_mapped_view)
