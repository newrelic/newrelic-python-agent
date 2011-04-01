# vi: set sw=4 expandtab :

import os
import traceback
import types

import _newrelic

def _fixup_database():
    from django.conf import settings

    if hasattr(settings, 'DATABASES'):
        for alias, database in settings.DATABASES.items():
            parts = database['ENGINE'].split('.')
            module = __import__(database['ENGINE'], fromlist='base')
            interface = module.base.Database

            # XXX Can probably just instrument database['ENGINE']
            # as that should be the database module name.

            _newrelic.wrap_database_trace(interface.__name__, 'Cursor',
                                   'execute', 1)
            _newrelic.wrap_database_trace(interface.__name__, 'Cursor',
                                   'executemany', 1)

    elif hasattr(settings, 'DATABASE_ENGINE'):
        _newrelic.wrap_database_trace(settings.DATABASE_ENGINE, 'Cursor',
                               'execute', 1)
        _newrelic.wrap_database_trace(settings.DATABASE_ENGINE, 'Cursor',
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

def _out_resolver_resolve(result):
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
    wrapper = _newrelic.OutFunctionWrapper(function, _out_resolver_resolve)
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

    _newrelic.wrap_web_transaction('django.core.handlers.wsgi', 'WSGIHandler',
                           '__call__', application)

    _newrelic.wrap_post_function('django.core.handlers.base','BaseHandler',
                                 'load_middleware', _fixup_middleware,
                                 run_once=True)

    _newrelic.wrap_post_function('django.core.urlresolvers','RegexURLPattern',
                                 '__init__', _fixup_resolver)

    _newrelic.wrap_pre_function('django.core.handlers.wsgi', 'WSGIHandler',
                                'handle_uncaught_exception', _fixup_exception)

    from django.template import Template
    if hasattr(Template, '_render'):
        _newrelic.wrap_function_trace('django.template', 'Template',
              '_render', lambda template, context: \
              '%s Template ' % template.name, 'Template')
    else:
        _newrelic.wrap_function_trace('django.template', 'Template',
              'render', lambda template, context: \
              '%s Template ' % template.name, 'Template')

    #_newrelic.wrap_function_trace('django.template', 'NodeList',
    #      'render_node', lambda template, node, context: \
    #      '%s Node ' % _newrelic.callable_name(node), 'Template')

    #_newrelic.wrap_function_trace('django.template.debug', 'DebugNodeList',
    #      'render_node', lambda template, node, context: \
    #      '%s Node ' % _newrelic.callable_name(node), 'Template')

    # This is not Django specific, but is an example of eternal node.

    try:
        import feedparser
    except:
        pass
    else:
        _newrelic.wrap_external_trace('feedparser', None, 'parse', 0)

    return settings
