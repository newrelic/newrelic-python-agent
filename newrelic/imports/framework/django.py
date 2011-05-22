from newrelic.agent import (FunctionTraceWrapper, OutFunctionWrapper,
        wrap_pre_function, wrap_post_function, wrap_function_trace,
        wrap_error_trace, callable_name, transaction, NameTransactionWrapper,
        transaction, settings, ErrorTraceWrapper, import_module)

def insert_rum(request, response):
    if not settings().browser_monitoring.auto_instrument:
        return response
    t = transaction()
    if not t:
        return response
    ctype = response.get('Content-Type', '').lower()
    if ctype != "text/html" and not ctype.startswith("text/html;"):
        return response
    header = t.browser_timing_header()
    footer = t.browser_timing_footer()
    if not header or not footer:
        return response
    start = response.content.find('<head')
    end = response.content.rfind('</body>', -1024)
    if start != -1 and end != -1:
        start = response.content.find('>', start, start+1024)
        if start != -1 and start < end:
            parts = []
            parts.append(response.content[0:start+1])
            parts.append(header)
            parts.append(response.content[start+1:end])
            parts.append(footer)
            parts.append(response.content[end:])
            response.content = ''
            content = ''.join(parts)
            response.content = content
    elif start == -1 and end != -1:
        start = response.content.find('<body')
        if start != -1 and start < end:
            parts = []
            parts.append(response.content[0:start])
            parts.append('<head>')
            parts.append(header)
            parts.append('</head>')
            parts.append(response.content[start:end])
            parts.append(footer)
            parts.append(response.content[end:])
            response.content = ''
            content = ''.join(parts)
            response.content = content
    return response

def newrelic_browser_timing_header():
    t = transaction()
    if not t:
        return ""
    return t.browser_timing_header()

def newrelic_browser_timing_footer():
    t = transaction()
    if not t:
        return ""
    return t.browser_timing_footer()

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

        # Insert middleware for inserting RUM header/footer.

        handler._response_middleware.insert(0, insert_rum)

    if hasattr(handler, '_exception_middleware'):
        exception_middleware = []
        for function in handler._exception_middleware:
            wrapper = FunctionTraceWrapper(function)
            exception_middleware.append(wrapper)

        handler._exception_middleware = exception_middleware

def wrap_url_resolver_output(result):
    if result is None:
        return

    # Note that adding an error trace wrapper means that if
    # there are no exception middleware that render a response
    # that error will be captured twice. In this case the
    # duplicate should get discarded later as will be for the
    # same exception type.

    if type(result) == type(()):
        callback, args, kwargs = result
        wrapper = NameTransactionWrapper(callback, None, 'Django')
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper)
        result = (wrapper, args, kwargs)
    else:
        wrapper = NameTransactionWrapper(result.func, None, 'Django')
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper)
        result.func = wrapper

    return result

def wrap_url_resolver(resolver, *args, **kwargs):
    function = resolver.resolve
    wrapper = OutFunctionWrapper(function, wrap_url_resolver_output)
    resolver.resolve = wrapper

def wrap_uncaught_exception(handler, request, resolver, exc_info):
    current_transaction = transaction()
    if current_transaction:
        current_transaction.notice_error(*exc_info)

def instrument(module):

    wrap_post_function('django.core.handlers.base',
            'BaseHandler.load_middleware',
            wrap_middleware, run_once=True)

    wrap_post_function('django.core.urlresolvers',
            'RegexURLPattern.__init__',
             wrap_url_resolver)

    wrap_pre_function('django.core.handlers.wsgi',
            'WSGIHandler.handle_uncaught_exception',
            wrap_uncaught_exception)

    wrap_error_trace('django.core.urlresolvers',
            'get_callable')

    if module.VERSION[:2] >= (1, 3):
        wrap_function_trace('django.template', 'Template._render',
                (lambda template, context: template.name), 'Template/Render')
    else:
        wrap_function_trace('django.template', 'Template.render',
                (lambda template, context: template.name), 'Template/Render')

    # These are label as potentially non interesting so they
    # will be dropped from transaction traces with too many
    # nodes if they don't consume a lot of time.

    wrap_function_trace('django.template', 'NodeList.render_node',
            (lambda template, node, context: callable_name(node)),
            None, interesting=False)

    wrap_function_trace('django.template.debug', 'DebugNodeList.render_node',
            (lambda template, node, context: callable_name(node)),
            None, interesting=False)

    # Register template tags for RUM header/footer.

    django_template = import_module('django.template')
    library = django_template.Library()
    library.simple_tag(newrelic_browser_timing_header)
    library.simple_tag(newrelic_browser_timing_footer)
    django_template.libraries['django.templatetags.newrelic'] = library
