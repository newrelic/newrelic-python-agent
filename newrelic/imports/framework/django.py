from newrelic.agent import (FunctionTraceWrapper, OutFunctionWrapper,
        wrap_pre_function, wrap_post_function, wrap_function_trace,
        wrap_error_trace, callable_name, transaction, NameTransactionWrapper,
        transaction, settings, ErrorTraceWrapper, wrap_in_function,
        WSGIApplicationWrapper, import_module, transaction)

import types

def insert_rum(request, response):

    # Only insert RUM JavaScript headers and footers if
    # enabled locally in configuration file.

    if not settings().browser_monitoring.auto_instrument:
        return response

    # Need to be running within a valid web transaction.

    t = transaction()
    if not t:
        return response

    # Only possible if the content type is text/html.

    ctype = response.get('Content-Type', '').lower()
    if ctype != "text/html" and not ctype.startswith("text/html;"):
        return response

    # No point continuing if header or footer is empty.
    # This can occur if RUM is not enabled within the UI
    # or notification about it being enabled in the UI
    # has not been received yet as process only just
    # started.

    header = t.browser_timing_header()
    footer = t.browser_timing_footer()
    if not header or not footer:
        return response

    # Make sure we flatten any content first as it could be
    # stored as a list of strings. Do this by assigning back
    # onto itself. This is done to avoid having multiple
    # copies of the string in memory at the same time as we
    # progress through steps below.

    content = response.content
    response.content = content

    # Insert the JavaScript. We require that there is a
    # <head> element in the HTML, otherwise we don't do
    # it. When updating response content we null the
    # original first to avoid multiple copies in memory
    # when we recompose actual response from list of
    # strings.
    #
    # XXX This needs to be updated to only insert after
    # any meta tags within the head section to avoid IE.
    # problems. See tracker issue 154789.

    start = content.find('<head')
    end = content.rfind('</body>', -1024)
    if start != -1 and end != -1:
        start = content.find('>', start, start+1024)
        if start != -1 and start < end:
            parts = []
            parts.append(content[0:start+1])
            parts.append(header)
            parts.append(content[start+1:end])
            parts.append(footer)
            parts.append(content[end:])
            response.content = ''
            content = ''.join(parts)
            response.content = content
    elif start == -1 and end != -1:
        start = content.find('<body')
        if start != -1 and start < end:
            parts = []
            parts.append(content[0:start])
            parts.append('<head>')
            parts.append(header)
            parts.append('</head>')
            parts.append(content[start:end])
            parts.append(footer)
            parts.append(content[end:])
            response.content = ''
            content = ''.join(parts)
            response.content = content

    # By inserting content we are invalidating any ETag,
    # so need to delete it. Can't assume we can
    # regenerate it using CommonMiddleware as that may
    # not have been the source of it.

    del response['ETag']

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
            wrapper = NameTransactionWrapper(function)
            wrapper = FunctionTraceWrapper(wrapper)
            request_middleware.append(wrapper)

        handler._request_middleware = request_middleware

    if hasattr(handler, '_view_middleware'):
        view_middleware = []
        for function in handler._view_middleware:
            wrapper = NameTransactionWrapper(function)
            wrapper = FunctionTraceWrapper(wrapper)
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
        wrapper = NameTransactionWrapper(callback)
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper,
                                    ignore_errors=['django.http.Http404'])
        result = (wrapper, args, kwargs)
    else:
        wrapper = NameTransactionWrapper(result.func, None)
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper,
                                    ignore_errors=['django.http.Http404'])
        result.func = wrapper

    return result

def wrap_url_resolver_404_output(result):
    if result is None:
        return

    callback, kwargs = result
    wrapper = NameTransactionWrapper(callback)
    wrapper = FunctionTraceWrapper(wrapper)
    result = (wrapper, kwargs)

    return result

class name_url_resolver_404(object):
    def __init__(self, wrapped):
        self.__wrapped__ = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, *args, **kwargs):
        current_transaction = transaction()
        if current_transaction:
            django_core_urlresolvers = import_module(
                    'django.core.urlresolvers')
            try:
                return self.__wrapped__(*args, **kwargs)
            except django_core_urlresolvers.Resolver404:
                current_transaction.name_transaction('404', 'Function')
                raise
            except:
                raise
        else:
            return self.__wrapped__(*args, **kwargs)

def wrap_url_resolver(resolver, *args, **kwargs):
    function = resolver.resolve
    wrapper = NameTransactionWrapper(function)
    wrapper = name_url_resolver_404(wrapper)
    wrapper = OutFunctionWrapper(wrapper, wrap_url_resolver_output)
    resolver.resolve = wrapper

    function = resolver.resolve404
    wrapper = OutFunctionWrapper(function, wrap_url_resolver_404_output)
    resolver.resolve404 = wrapper

def wrap_uncaught_exception(handler, request, resolver, exc_info):
    current_transaction = transaction()
    if current_transaction:
        current_transaction.notice_error(*exc_info)

def wrap_add_wsgi_application_input(self, application, **kwargs):
    return ((self, WSGIApplicationWrapper(application)), kwargs)

def instrument(module):

    if module.__name__ == 'django.core.handlers.base':
        wrap_post_function(module, 'BaseHandler.load_middleware',
                wrap_middleware, run_once=True)

    elif module.__name__ == 'django.core.handlers.wsgi':
        wrap_pre_function(module, 'WSGIHandler.handle_uncaught_exception',
                wrap_uncaught_exception)

    elif module.__name__ == 'django.core.urlresolvers':
        wrap_post_function(module, 'RegexURLResolver.__init__',
                 wrap_url_resolver)
        wrap_error_trace(module, 'get_callable',
                 ignore_errors=['django.http.Http404'])

    elif module.__name__ == 'django.template':
        if hasattr(module.Template, '_render'):
            wrap_function_trace(module, 'Template._render',
                    (lambda template, context: template.name),
                    'Template/Render')
        else:
            wrap_function_trace(module, 'Template.render',
                    (lambda template, context: template.name),
                    'Template/Render')

        # Register template tags for RUM header/footer.

        library = module.Library()
        library.simple_tag(newrelic_browser_timing_header)
        library.simple_tag(newrelic_browser_timing_footer)
        module.libraries['django.templatetags.newrelic'] = library

    elif module.__name__ == 'django.core.servers.basehttp':

        # Allow 'runserver' to be used with Django <= 1.3.
        # Later versions of Django use wsgiref server instead.

        if hasattr(module.ServerHandler, 'run'):
            wrap_in_function(module, 'ServerHandler.run',
                    wrap_add_wsgi_application_input)
