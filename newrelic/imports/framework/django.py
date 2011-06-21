from newrelic.agent import (
        import_module,
        settings,
        transaction,
        wrap_function_trace,
        wrap_in_function,
        wrap_out_function,
        wrap_post_function,
        wrap_pre_function,
        wrap_error_trace,
        ErrorTraceWrapper,
        FunctionTraceWrapper,
        NameTransactionWrapper,
        ObjectWrapper,
        OutFunctionWrapper,
        WSGIApplicationWrapper)

def response_middleware_browser_monitoring(request, response):

    # Only insert RUM JavaScript headers and footers if
    # enabled locally in configuration file.

    if not settings().browser_monitoring.auto_instrument:
        return response

    # Need to be running within a valid web transaction.

    txn = transaction()
    if not txn:
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

    header = txn.browser_timing_header()
    footer = txn.browser_timing_footer()
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
    txn = transaction()
    if not txn:
        return ""
    return txn.browser_timing_header()

def newrelic_browser_timing_footer():
    txn = transaction()
    if not txn:
        return ""
    return txn.browser_timing_footer()

def post_BaseHandler_load_middleware(handler, *args, **kwargs):

    # This gets executed after the first time that the
    # load_middleware() method of BaseHandler is called.
    # It only gets executed once as don't want to do all
    # this on every time it is called.

    # First go through all the request middleware and
    # wrap them. Do this to record time within the
    # middleware, but also to bind web transaction name
    # based on middleware name. We need to do the latter
    # even though we bind name again later as the request
    # middleware can return a response immediately.

    if hasattr(handler, '_request_middleware'):
        request_middleware = []
        for function in handler._request_middleware:
            wrapper = NameTransactionWrapper(function)
            wrapper = FunctionTraceWrapper(wrapper)
            request_middleware.append(wrapper)
        handler._request_middleware = request_middleware

    # Now go through all the view middleware and wrap
    # them also. Do this to record time within the
    # middleware, but again to bind web transaction name
    # based on middleware name. We need to do the latter
    # even though we bind name again later as the view
    # middleware can return a response immediately even
    # by that point a view handler has been chosen. When
    # this occurs the view handler is never actually
    # called and so use the view middleware name for web
    # transaction name.

    if hasattr(handler, '_view_middleware'):
        view_middleware = []
        for function in handler._view_middleware:
            wrapper = NameTransactionWrapper(function)
            wrapper = FunctionTraceWrapper(wrapper)
            view_middleware.append(wrapper)
        handler._view_middleware = view_middleware

    # Now go through all the template response
    # middleware and wrap them also. Do this to record
    # time within the middleware. We don't bind web
    # transaction name to the template response
    # middleware name as this gets executed after view
    # handler and we want to preserve the view handler
    # name as web transaction name. Note that template
    # response middleware don't exist in older versions
    # of Django but we only wrap them if the list of
    # template response middleware exists, so is okay.

    if hasattr(handler, '_template_response_middleware'):
        template_response_middleware = []
        for function in handler._template_response_middleware:
            wrapper = FunctionTraceWrapper(function)
            template_response_middleware.append(wrapper)
        handler._template_response_middleware = template_response_middleware

    # Now go through all the response middleware and
    # wrap them also. Do this to record time within the
    # middleware. Again, we preserve the web transaction
    # name as that for the view handler.

    if hasattr(handler, '_response_middleware'):
        response_middleware = []
        for function in handler._response_middleware:
            wrapper = FunctionTraceWrapper(function)
            response_middleware.append(wrapper)
        handler._response_middleware = response_middleware

    # Now go through all the exception middleware and
    # wrap them also. Do this to record time within the
    # middleware and name the web transaction. We do
    # the latter to highlight when an exception has
    # occurred and been processed by the the exception
    # middleware otherwise they bind to the name for
    # the view handler still and don't show out as well.

    if hasattr(handler, '_exception_middleware'):
        exception_middleware = []
        for function in handler._exception_middleware:
            wrapper = NameTransactionWrapper(function)
            wrapper = FunctionTraceWrapper(wrapper)
            exception_middleware.append(wrapper)
        handler._exception_middleware = exception_middleware

    # Insert response middleware for automatically
    # inserting end user monitoring header and footer.

    if hasattr(handler, '_response_middleware'):
        handler._response_middleware.insert(0,
                response_middleware_browser_monitoring)

class name_RegexURLResolver_resolve_Resolver404(ObjectWrapper):
    def __call__(self, *args, **kwargs):

	# Captures a Resolver404 exception and names the
	# web transaction as a generic 404 with scope
	# 'Uri'. This is to avoid problem of metric
	# explosion on URLs which didn't actually map to
	# a valid resource. If there is a 404 handler then
        # this will get overriden again later so this is
        # just a default for where not 404 handler.

        txn = transaction()
        if txn:
            Resolver404 = import_module(
                    'django.core.urlresolvers').Resolver404
            try:
                return self.wrapped(*args, **kwargs)
            except Resolver404:
                txn.name_transaction('404', scope='Uri')
                raise
            except:
                raise
        else:
            return self.wrapped(*args, **kwargs)

def out_RegexURLResolver_resolve(result):

    # The resolve() method is what returns the view
    # handler to be executed for a specific request. The
    # format of the data structure which is returned has
    # changed across Django versions so need to adapt
    # automatically to which format of data is used.

    if result is None:
        return result

    txn = transaction()
    if not txn:
        return result

    # We wrap the actual view handler callback to use
    # its name to name the web transaction, for timing
    # the call and capturing exceptions. We also have
    # special case where we name web transaction as a
    # generic 404 where we get a Resolver404 exception.
    # For the case of where there is no exception
    # middleware the exception will be captured and
    # recorded a second time by the uncaught exception
    # handler. We can't though rely on just catching
    # here it though, as the uncaught exception handler
    # is also used to look out for exceptions in
    # subsequent middleware as well. So can't avoid
    # capturing it twice. The duplicate error will at
    # some point be ignored as the exception type and
    # description will be the same so ultimately doesn't
    # matter. We ignore Http404 exceptions here as we
    # don't want top capture as error details a
    # legitimate response from a view handler indicating
    # that the resource mapped by the URL did not exist.

    if type(result) == type(()):
        callback, callback_args, callback_kwargs = result
        wrapper = NameTransactionWrapper(callback)
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper,
                ignore_errors=['django.http.Http404'])
        wrapper = name_RegexURLResolver_resolve_Resolver404(wrapper)
        result = (wrapper, callback_args, callback_kwargs)
    else:
        wrapper = NameTransactionWrapper(result.func, None)
        wrapper = FunctionTraceWrapper(wrapper)
        wrapper = ErrorTraceWrapper(wrapper,
                ignore_errors=['django.http.Http404'])
        wrapper = name_RegexURLResolver_resolve_Resolver404(wrapper)
        result.func = wrapper

    return result

def out_RegexURLResolver_resolve404(result):

    # The resolve404() method is what returns a handler
    # for 404 responses from view handler or middleware.

    if result is None:
        return

    txn = transaction()
    if not txn:
        return result

    # We wrap the actual handler callback to use its
    # name to name the web transaction and for timing.
    # We don't need to wrap it to capture errors as any
    # errors from this handler always get handled by the
    # uncaught exception handler.

    callback, param_dict = result
    wrapper = NameTransactionWrapper(callback)
    wrapper = FunctionTraceWrapper(wrapper)
    result = (wrapper, param_dict)

    return result

def pre_WSGIHandler_handle_uncaught_exception(handler, request,
            resolver, exc_info):

    # Record the exception details passed into the
    # function against the current transaction object.

    txn = transaction()
    if txn:
        txn.notice_error(*exc_info)

def name_Template_render(template, context):
    
    # Use the name of the template as held by the
    # template object itself. This should be a relative
    # path with the template loader uniquely associated
    # it with a specific template library. Therefore do
    # not need to worry about making it absolute as
    # meaning should be known in the context of the
    # specific Django site.

    return template.name

def in_ServerHandler_run(self, application, **kwargs):

    # Wrap the WSGI application argument on the way in
    # so that run() method gets the wrapped instance.

    return ((self, WSGIApplicationWrapper(application)), kwargs)

def instrument(module):

    if module.__name__ == 'django.core.handlers.base':

	# Attach a post function to load_middleware() method of
	# BaseHandler so that we can iterate over the various
	# middleware and wrap them all with a function trace.
	# The load_middleware() function can be called more than
        # once with it returning if it doesn't need to do anything.
        # We only want to do the wrapping once though so the post
        # function is flagged to only run once.

        wrap_post_function(module, 'BaseHandler.load_middleware',
                post_BaseHandler_load_middleware, run_once=True)

    elif module.__name__ == 'django.core.handlers.wsgi':

	# Attach a pre function to handle_uncaught_exception()
	# of WSGIHandler so that can capture exception details
	# of any exception which wasn't caught and dealt with by
	# an exception middleware. The handle_uncaught_exception()
	# function produces a 500 error response page and
	# otherwise suppresses the exception, so last chance to
        # do this as exception will not propogate up to the WSGI
        # application.

        wrap_pre_function(module, 'WSGIHandler.handle_uncaught_exception',
                pre_WSGIHandler_handle_uncaught_exception)

    elif module.__name__ == 'django.core.urlresolvers':

	# Wrap method which maps a string version of a function
	# name as used in urls.py patter so can capture any
	# exception which is raised during that process.
	# Normally Django captures import errors at this point
	# and then reraises a ViewDoesNotExist exception with
	# details of the original error and traceback being
	# lost. We thus intercept it here so can capture that
	# traceback which is otherwise lost. Although we ignore
	# a Http404 exception here, it probably is never the
	# case that one can be raised by get_callable().

        wrap_error_trace(module, 'get_callable',
                ignore_errors=['django.http.Http404'])

        # Wrap methods which resolves a request to a view
        # handler. This can be called against a resolver
        # initialised against a custom URL conf associated
        # with a specific request, of a resolver which uses
        # the default URL conf.

        wrap_out_function(module, 'RegexURLResolver.resolve',
                out_RegexURLResolver_resolve)

        wrap_out_function(module, 'RegexURLResolver.resolve404',
                out_RegexURLResolver_resolve404)

    elif module.__name__ == 'django.template':

        # Wrap methods for rendering of Django templates. The
        # name of the method changed in between Django versions
        # so need to check for which one we have. The name of
        # the function trace node is taken from the name of the
        # template. An explicit scope is given so can recognise
        # this as template rendering time.

        if hasattr(module.Template, '_render'):
            wrap_function_trace(module, 'Template._render',
                    name=name_Template_render, scope='Template/Render')
        else:
            wrap_function_trace(module, 'Template.render',
                    name=name_Template_render, scope='Template/Render')

        # Register template tags for RUM header/footer.
        #
        # XXX This needs to be separated out into a Django
        # application and no longer added automaticaly. Instead
        # would be up to user to add a New Relic application
        # into INSTALLED_APPS to get access to the template tag
        # library for browser monitoring. Note that these don't
        # have to be installed for auto RUM to work.

        library = module.Library()
        library.simple_tag(newrelic_browser_timing_header)
        library.simple_tag(newrelic_browser_timing_footer)
        module.libraries['django.templatetags.newrelic'] = library

    elif module.__name__ == 'django.core.servers.basehttp':

        # Allow 'runserver' to be used with Django <= 1.3.
        # Later versions of Django use wsgiref server instead
        # which will be dealt with via instrumentation of the
        # wsgiref module instead.

        if hasattr(module.ServerHandler, 'run'):
            wrap_in_function(module, 'ServerHandler.run',
                    in_ServerHandler_run)
