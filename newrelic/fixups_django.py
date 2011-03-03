# vi: set sw=4 expandtab :

import os
import traceback

import _newrelic

from fixups import _wrap_wsgi_application

def _fixup_database():
    from django.conf import settings

    # TODO Need to cope with old single database config.

    if hasattr(settings, 'DATABASES'):
        for alias, database in settings.DATABASES.items():
            parts = database['ENGINE'].split('.')
            module = __import__(database['ENGINE'], fromlist='base')
            interface = module.base.Database

            if interface.__name__ == 'sqlite3.dbapi2':
                _newrelic.wrap_database_trace('sqlite3', 'Cursor',
                                       'execute', 1)
                _newrelic.wrap_database_trace('sqlite3', 'Cursor',
                                       'executemany', 1)

def _fixup_middleware(handler, *args, **kwargs):
    if hasattr(handler, '_request_middleware'):
        request_middleware = []
        for function in handler._request_middleware:
            wrapper = _newrelic.FunctionTraceWrapper(function,
                    scope='RequestMiddleware')
            request_middleware.append(wrapper)

        handler._request_middleware = request_middleware

    if hasattr(handler, '_view_middleware'):
        view_middleware = []
        for function in handler._view_middleware:
            wrapper = _newrelic.FunctionTraceWrapper(function,
                    scope='ViewMiddleware')
            view_middleware.append(wrapper)

        handler._view_middleware = view_middleware

    if hasattr(handler, '_template_response_middleware'):
        template_response_middleware = []
        for function in handler._template_response_middleware:
            wrapper = _newrelic.FunctionTraceWrapper(function,
                    scope='TemplateResponseMiddleware')
            template_response_middleware.append(wrapper)

        handler._template_response_middleware = template_response_middleware

    if hasattr(handler, '_response_middleware'):
        response_middleware = []
        for function in handler._response_middleware:
            wrapper = _newrelic.FunctionTraceWrapper(function,
                    scope='ResponseMiddleware')
            response_middleware.append(wrapper)

        handler._response_middleware = response_middleware

    if hasattr(handler, '_exception_middleware'):
        exception_middleware = []
        for function in handler._exception_middleware:
            wrapper = _newrelic.FunctionTraceWrapper(function,
                    scope='ExceptionMiddleware')
            exception_middleware.append(wrapper)

        handler._exception_middleware = exception_middleware

    _fixup_database()

def _pass_resolver_resolve(result):
    if result is None:
        return

    if type(result) == type(()):
        callback, args, kwargs = result
        callback = _newrelic.FunctionTraceWrapper(callback,
                scope='ViewFunction', override_path=True)
        result = (callback, args, kwargs)
    else:
        result.func = _newrelic.FunctionTraceWrapper(result.func,
                scope='ViewFunction', override_path=True)

    return result

def _fixup_resolver(resolver, *args, **kwargs):
    function = resolver.resolve
    wrapper = _newrelic.PassFunctionWrapper(function, _pass_resolver_resolve)
    resolver.resolve = wrapper

def _fixup_exception(handler, request, resolver, exc_info):
    transaction = _newrelic.transaction()
    if transaction:
        transaction.runtime_error(*exc_info)

def _instrument(application):
    import django

    settings = {}

    settings['django.version'] = django.get_version()
    settings['django.path'] = os.path.dirname(django.__file__)

    _wrap_wsgi_application('django.core.handlers.wsgi', 'WSGIHandler',
                           '__call__', application)

    _newrelic.wrap_post_function('django.core.handlers.base','BaseHandler',
                                 'load_middleware', _fixup_middleware,
                                 run_once=True)

    _newrelic.wrap_post_function('django.core.urlresolvers','RegexURLPattern',
                                 '__init__', _fixup_resolver)

    _newrelic.wrap_pre_function('django.core.handlers.wsgi', 'WSGIHandler',
                                'handle_uncaught_exception', _fixup_exception)

    if django.VERSION < (1, 3, 0):
        _newrelic.wrap_function_trace('django.template', 'Template', 'render',
                             scope='Template')
    else:
        _newrelic.wrap_function_trace('django.template.base', 'Template', 'render',
                             scope='Template')

    _newrelic.wrap_function_trace('django.template.loader', None,
                         'find_template_loader', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'find_template', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'find_template_source', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'get_template', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'get_template_from_string', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'render_to_string', scope='Template')
    _newrelic.wrap_function_trace('django.template.loader', None,
                         'select_template', scope='Template')

    return settings
