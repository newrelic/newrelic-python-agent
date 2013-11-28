from newrelic.agent import (callable_name, current_transaction,
        wrap_callable, wrap_out_function, wrap_wsgi_application,
        FunctionTrace, global_settings)

def instrument_pyramid_router(module):
    pyramid_version = None

    try:
        import pkg_resources
        pyramid_version = pkg_resources.get_distribution('pyramid').version
    except Exception:
        pass

    wrap_wsgi_application(module, 'Router.__call__',
            framework=('Pyramid', pyramid_version))

def should_ignore(exc, value, tb):
    from pyramid.httpexceptions import HTTPException
    # Ignore certain exceptions based on HTTP status codes. The default list
    # of status codes are defined in the settings.error_collector object.

    settings = global_settings()
    if (isinstance(value, HTTPException) and (value.code in
                    settings.error_collector.ignore_status_codes)):
        return True

    # TODO: In a pyramid application, a class with a get and post method will
    # raise a PredicateMismatch exception whenever a GET or POST request is
    # made to that class in order to route the request to the right method.
    # Since PredicateMismatch is a derived class from NotFound exception it
    # will automatically ignored by the status code match above. But if a
    # customer chooses to not ignore 404 then he will get a bunch of
    # PredicateMismatch exceptions each time a request is routed to the class.
    # So we're ignoring PredicateMismatch by name.
    #
    # The risk here is when a method (such as DELETE) is not defined on the
    # class, it will raise a PredicateMismatch exception which will be
    # suppressed. So there is no current distinction between a
    # PredicateMismatch thrown to route the request and a PredicateMismatch
    # thrown as a result of missing method.

    # Ignore based on exception name.

    module = value.__class__.__module__
    name = value.__class__.__name__
    fullname = '%s:%s' % (module, name)

    ignore_exceptions = ('pyramid.exceptions.PredicateMismatch',)

    if fullname in ignore_exceptions:
        return True

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
        try:
            return wrapped(*args, **kwargs)

        except:  # Catch all
            transaction.record_exception(ignore_errors=should_ignore)
            raise

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
