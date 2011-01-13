# vi: set sw=4 expandtab :

import os
import traceback

from fixups import (_wrap_pre_function, _wrap_post_function,
                    _wrap_web_transaction, _pass_function,
                   _wrap_function_trace)
from decorators import function_trace
from middleware import current_transaction

import _newrelic

# TODO Database cursors.
# TODO URL path mapped to view name.

def _wrap_c_database_trace(mname, cname, fname, argnum):
    print mname, cname, fname, argnum
    return _newrelic.wrap_c_database_trace(mname, cname, fname, argnum)

def _fixup_database():
    from django.conf import settings

    # TODO Need to cope with old single database config.

    if hasattr(settings, 'DATABASES'):
        for alias, database in settings.DATABASES.items():
            print 'DATABASE', database['ENGINE']
            parts = database['ENGINE'].split('.')
            module = __import__(database['ENGINE'], fromlist='base')
            interface = module.base.Database

            if interface.__name__ == 'sqlite3.dbapi2':
                _wrap_c_database_trace('sqlite3.dbapi2', 'Cursor',
                                       'execute', 1)
                _wrap_c_database_trace('sqlite3.dbapi2', 'Cursor',
                                       'executemany', 1)

def _fixup_middleware(handler, *args, **kwargs):
    if hasattr(handler, '_request_middleware'):
        request_middleware = []
        for function in handler._request_middleware:
            wrapper = function_trace()(function)
            request_middleware.append(wrapper)

        handler._request_middleware = request_middleware

    if hasattr(handler, '_view_middleware'):
        view_middleware = []
        for function in handler._view_middleware:
            wrapper = function_trace()(function)
            view_middleware.append(wrapper)

        handler._view_middleware = view_middleware

    if hasattr(handler, '_template_response_middleware'):
        template_response_middleware = []
        for function in handler._template_response_middleware:
            wrapper = function_trace()(function)
            template_response_middleware.append(wrapper)

        handler._template_response_middleware = template_response_middleware

    if hasattr(handler, '_response_middleware'):
        response_middleware = []
        for function in handler._response_middleware:
            wrapper = function_trace()(function)
            response_middleware.append(wrapper)

        handler._response_middleware = response_middleware

    if hasattr(handler, '_exception_middleware'):
        exception_middleware = []
        for function in handler._exception_middleware:
            wrapper = function_trace()(function)
            exception_middleware.append(wrapper)

        handler._exception_middleware = exception_middleware

    _fixup_database()

def _pass_resolver_resolve(result):
    if result is None:
        return

    if type(result) == type(()):
        callback, args, kwargs = result
        callback = function_trace(override_path=True)(callback)
        result = (callback, args, kwargs)
    else:
        result.func = function_trace(override_path=True)(result.func)

    return result

def _fixup_resolver(resolver, *args, **kwargs):
    function = resolver.resolve
    wrapper = _pass_function(_pass_resolver_resolve)(function)
    resolver.resolve = wrapper

def _fixup_exception(handler, request, resolver, exc_info):
    transaction = current_transaction()
    transaction.runtime_error(str(exc_info[1]), type(exc_info[1]).__name__,
            ''.join(traceback.format_exception(*exc_info)))

def _instrument(application):
    import django

    settings = {}

    settings['django.version'] = django.get_version()
    settings['django.path'] = os.path.dirname(django.__file__)

    _wrap_web_transaction('django.core.handlers.wsgi', 'WSGIHandler',
                          '__call__', application)

    _wrap_post_function('django.core.handlers.base','BaseHandler',
                        'load_middleware', _fixup_middleware)

    _wrap_post_function('django.core.urlresolvers','RegexURLPattern',
                        '__init__', _fixup_resolver)

    _wrap_pre_function('django.core.handlers.wsgi', 'WSGIHandler',
                          'handle_uncaught_exception', _fixup_exception)

    if django.VERSION < (1, 3, 0):
        _wrap_function_trace('django.template', 'Template', 'render')
    else:
        _wrap_function_trace('django.template.base', 'Template', 'render')

    _wrap_function_trace('django.template.loader', None,
                         'find_template_loader')
    _wrap_function_trace('django.template.loader', None,
                         'find_template')
    _wrap_function_trace('django.template.loader', None,
                         'find_template_source')
    _wrap_function_trace('django.template.loader', None,
                         'get_template')
    _wrap_function_trace('django.template.loader', None,
                         'get_template_from_string')
    _wrap_function_trace('django.template.loader', None,
                         'render_to_string')
    _wrap_function_trace('django.template.loader', None,
                         'select_template')

    return settings
