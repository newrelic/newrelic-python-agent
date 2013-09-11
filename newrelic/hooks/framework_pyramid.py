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
            'pyramid.httpexceptions:HTTPNotFound',
            'pyramid.exceptions:PredicateMismatch']):
            return wrapped(*args, **kwargs)

def wrap_view_handler(mapped_view):
    return wrap_callable(mapped_view, view_handler_wrapper)

def default_view_mapper_wrapper(wrapped, instance, args, kwargs):
    wrapper = wrapped(*args, **kwargs)

    def _args(view, *args, **kwargs):
        return view

    view = _args(*args, **kwargs)

    def _wrapper(context, request):
        transaction = current_transaction()

        if not transaction:
            return wrapper(context, request)

        name = callable_name(view)

        with FunctionTrace(transaction, name=name) as tracer:
            try:
                return wrapper(context, request)
            finally:
                attr = instance.attr
                if attr:
                    inst = getattr(request, '__view__', None)
                    if inst is not None:
                        name = callable_name(getattr(inst, attr))
                        transaction.set_transaction_name(name, priority=1)
                        tracer.name = name
                else:
                    inst = getattr(request, '__view__', None)
                    if inst is not None:
                        method = getattr(inst, '__call__')
                        if method:
                            name = callable_name(method)
                            transaction.set_transaction_name(name, priority=1)
                            tracer.name = name

    return _wrapper

def instrument_pyramid_config_views(module):
    # Location of the ViewDeriver class changed from pyramid.config to
    # pyramid.config.views so check if present before trying to update.

    if hasattr(module, 'ViewDeriver'):
        wrap_out_function(module, 'ViewDeriver.__call__',
                wrap_view_handler)

    if hasattr(module, 'DefaultViewMapper'):
        module.DefaultViewMapper.map_class_requestonly = wrap_callable(
                module.DefaultViewMapper.map_class_requestonly,
                default_view_mapper_wrapper)
        module.DefaultViewMapper.map_class_native = wrap_callable(
                module.DefaultViewMapper.map_class_native,
                default_view_mapper_wrapper)
