from newrelic.agent import (FunctionTraceWrapper, OutFunctionWrapper,
        wrap_pre_function, wrap_post_function, wrap_function_trace,
        wrap_error_trace, callable_name, transaction)

def wrap_middleware(handler, *args, **kwargs):
    if hasattr(handler, '_request_middleware'):
        request_middleware = []
        for function in handler._request_middleware:
            wrapper = FunctionTraceWrapper(function)
            request_middleware.append(wrapper)

        handler._request_middleware = request_middleware

    if hasattr(handler, '_view_middleware'):
        view_middleware = []
        for function in handler._view_middleware:
            wrapper = FunctionTraceWrapper(function)
            view_middleware.append(wrapper)

        handler._view_middleware = view_middleware

    if hasattr(handler, '_template_response_middleware'):
        template_response_middleware = []
        for function in handler._template_response_middleware:
            wrapper = FunctionTraceWrapper(function)
            template_response_middleware.append(wrapper)

        handler._template_response_middleware = template_response_middleware

    if hasattr(handler, '_response_middleware'):
        response_middleware = []
        for function in handler._response_middleware:
            wrapper = FunctionTraceWrapper(function)
            response_middleware.append(wrapper)

        handler._response_middleware = response_middleware

    if hasattr(handler, '_exception_middleware'):
        exception_middleware = []
        for function in handler._exception_middleware:
            wrapper = FunctionTraceWrapper(function)
            exception_middleware.append(wrapper)

        handler._exception_middleware = exception_middleware

def wrap_url_resolver_result(result):
    if result is None:
        return

    if type(result) == type(()):
        callback, args, kwargs = result
        callback = FunctionTraceWrapper(callback, override_path=True)
        result = (callback, args, kwargs)
    else:
        result.func = FunctionTraceWrapper(result.func, override_path=True)

    return result

def wrap_url_resolver(resolver, *args, **kwargs):
    function = resolver.resolve
    wrapper = OutFunctionWrapper(function, wrap_url_resolver_result)
    resolver.resolve = wrapper

def wrap_uncaught_exception(handler, request, resolver, exc_info):
    current_transaction = transaction()
    if current_transaction:
        current_transaction.runtime_error(*exc_info)

def instrument(module):

    #wrap_web_transaction('django.core.handlers.wsgi', 'WSGIHandler',
    #                       '__call__', application)

    wrap_post_function('django.core.handlers.base','BaseHandler',
            'load_middleware', wrap_middleware, run_once=True)

    wrap_post_function('django.core.urlresolvers','RegexURLPattern',
            '__init__', wrap_url_resolver)

    wrap_pre_function('django.core.handlers.wsgi', 'WSGIHandler',
            'handle_uncaught_exception', wrap_uncaught_exception)

    wrap_error_trace('django.core.urlresolvers', None, 'get_callable')

    from django.template import Template

    if hasattr(Template, '_render'):
        wrap_function_trace('django.template', 'Template', '_render',
                lambda template, context: '%s Template ' % template.name)
    else:
        wrap_function_trace('django.template', 'Template', 'render',
                lambda template, context: '%s Template ' % template.name)

    #wrap_function_trace('django.template', 'NodeList', 'render_node',
    #        lambda template, node, context: '%s Node ' %
    #        callable_name(node))

    #wrap_function_trace('django.template.debug', 'DebugNodeList',
    #      'render_node', lambda template, node, context: '%s Node ' %
    #      callable_name(node))
