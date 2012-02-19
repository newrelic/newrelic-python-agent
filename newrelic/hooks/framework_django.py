from __future__ import with_statement

import sys
import types
import threading

import newrelic.api.transaction
import newrelic.api.function_trace
import newrelic.api.in_function
import newrelic.api.pre_function
import newrelic.api.post_function
import newrelic.api.error_trace
import newrelic.api.name_transaction
import newrelic.api.web_transaction
import newrelic.api.object_wrapper

# Response middleware for automatically inserting RUM header and
# footer into HTML response returned by application

def browser_timing_middleware(request, response):

    # Need to be running within a valid web transaction.

    transaction = newrelic.api.transaction.transaction()

    if not transaction:
        return response

    # Only insert RUM JavaScript headers and footers if enabled
    # in configuration.

    if not transaction.settings.rum.enabled:
        return response

    if transaction.autorum_disabled:
        return response

    # Only possible if the content type is text/html.

    ctype = response.get('Content-Type', '').lower()

    if ctype != "text/html" and not ctype.startswith("text/html;"):
        return response

    # Don't risk it if content encoding already set.

    if response.has_header('Content-Encoding'):
        return response

    # No point continuing if header or footer is empty. This can
    # occur if RUM is not enabled within the UI.

    header = transaction.browser_timing_header()
    footer = transaction.browser_timing_footer()

    if not header or not footer:
        return response

    # Make sure we flatten any content first as it could be
    # stored as a list of strings in the response object. We
    # assign it back to the response object to avoid having
    # multiple copies of the string in memory at the same time
    # as we progress through steps below.

    content = response.content
    response.content = content

    # Insert the JavaScript. If there is no <head> element we
    # insert our own containing the JavaScript. If we detect
    # possibility of IE compatibility mode then we insert
    # JavaScript at end of the <head> element. In other cases
    # insert at the start of the <head> element.
    #
    # When updating response content we null the original first
    # to avoid multiple copies in memory when we recompose the
    # actual response from list of strings.

    start = content.find('<head')
    end = content.rfind('</body>', -1024)
    if start != -1 and end != -1:
        offset = content.find('</head>', start)
        if content.find('X-UA-Compatible', start, offset) == -1:
            start = content.find('>', start, start+1024)
        elif offset != -1:
            start = offset - 1
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

    response['Content-Length'] = str(len(response.content))

    return response

def register_browser_timing_middleware(middleware):

    # Inserts our middleware for inserting the RUM header and
    # footer into the list of middleware. Must check for certain
    # types of middleware which modify content as must always
    # come before them. Otherwise is added last so that comes
    # after any caching middleware. If don't do that then the
    # inserted header and footer will end up being cached and
    # then when served up from cache we would add a second
    # header and footer, something we don't want.

    content_type_modifying_middleware = [
        'django.middleware.gzip:GZipMiddleware.process_response'
    ]

    for i in range(len(middleware)):
        function = middleware[i]
        name = newrelic.api.object_wrapper.callable_name(function)
        if name in content_type_modifying_middleware:
            middleware.insert(i, browser_timing_middleware)
            break
    else:
        middleware.append(browser_timing_middleware)

# Template tag functions for manually inserting RUM header and
# footer into HTML response. A template tag library for
# 'newrelic' will be automatically inserted into set of tag
# libraries when performing step to instrument the middleware.

def newrelic_browser_timing_header():
    transaction = newrelic.api.transaction.transaction()
    if not transaction:
        return ""
    return transaction.browser_timing_header()

def newrelic_browser_timing_footer():
    transaction = newrelic.api.transaction.transaction()
    if not transaction:
        return ""
    return transaction.browser_timing_footer()

# Addition of instrumentation for middleware. Can only do this
# after Django itself has constructed the list of middleware. We
# also insert the RUM middleware into the response middleware.

middleware_instrumentation_lock = threading.Lock()

class PreViewMiddlewareWrapper(object):

    # Wrapper to be applied to all the middleware which come before the
    # view handler. Records the time spent in the middleware as separate
    # function node and also attempts to name the web transaction after
    # the name of the middleware with success being determined by the
    # priority.

    def __init__(self, wrapped, priority):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped
        self.__priority = priority

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor, self.__priority)

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            before = (transaction.name, transaction.group)
            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name=self.__name):
                try:
                    result = self.__wrapped(*args, **kwargs)
                    after = (transaction.name, transaction.group)
                    if result and before == after:
                        transaction.name_transaction(self.__name,
                                priority=self.__priority)
                    return result
                except:
                    after = (transaction.name, transaction.group)
                    if before == after:
                        transaction.name_transaction(self.__name,
                                priority=self.__priority)
                    raise
        else:
            return self.__wrapped(*args, **kwargs)

def wrap_pre_view_middleware(middleware, priority):
    return [PreViewMiddlewareWrapper(function, priority)
            for function in middleware]

class PostViewMiddlewareWrapper(object):

    # Wrapper to be applied to all the middleware which come after the
    # view handler. Records the time spent in the middleware as separate
    # function node and also attempts to name the web transaction after
    # the name of the middleware with success being determined by the
    # priority.

    def __init__(self, wrapped, priority):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped
        self.__priority = priority

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor, self.__priority)

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name=self.__name):
                return self.__wrapped(*args, **kwargs)
        else:
            return self.__wrapped(*args, **kwargs)

def wrap_post_view_middleware(middleware, priority):
    return [PostViewMiddlewareWrapper(function, priority)
            for function in middleware]

def insert_and_wrap_middleware(handler, *args, **kwargs):

    # Use lock to control access by single thread but also as
    # flag to indicate if done the initialisation. Lock will be
    # None if have already done this.

    global middleware_instrumentation_lock

    if not middleware_instrumentation_lock:
        return

    lock = middleware_instrumentation_lock

    lock.acquire()

    # Check again in case two threads grab lock at same time.

    if not middleware_instrumentation_lock:
        lock.release()
        return

    # Set lock to None so we know have done the initialisation.

    middleware_instrumentation_lock = None

    try:
        # For response middleware, need to add in middleware for
        # automatically inserting RUM header and footer. This is
        # done first which means it gets wrapped and timed as
        # well. Will therefore show in traces however that may
        # be beneficial as highlights we are doing some magic
        # and can see if it is taking too long on large
        # responses.

        if hasattr(handler, '_response_middleware'):
            register_browser_timing_middleware(handler._response_middleware)

        # Now wrap the middleware to undertake timing and name
        # the web transaction. The naming is done as lower
        # priority than that for view handler so view handler
        # name always takes precedence.

        if hasattr(handler, '_request_middleware'):
            handler._request_middleware = wrap_pre_view_middleware(
                    handler._request_middleware, priority=2)

        if hasattr(handler, '_view_middleware'):
            handler._view_middleware = wrap_pre_view_middleware(
                    handler._view_middleware, priority=2)

        if hasattr(handler, '_template_response_middleware'):
            handler._template_response_middleware = wrap_post_view_middleware(
                  handler._template_response_middleware, priority=1)

        if hasattr(handler, '_response_middleware'):
            handler._response_middleware = wrap_post_view_middleware(
                    handler._response_middleware, priority=1)

        if hasattr(handler, '_exception_middleware'):
            handler._exception_middleware = wrap_post_view_middleware(
                    handler._exception_middleware, priority=1)

    finally:
        lock.release()

# Post import hooks for modules.

def instrument_django_core_handlers_base(module):

    # Attach a post function to load_middleware() method of
    # BaseHandler to trigger insertion of browser timing
    # middleware and wrapping of middleware for timing etc.

    newrelic.api.post_function.wrap_post_function(
            module, 'BaseHandler.load_middleware',
            insert_and_wrap_middleware)

class UncaughtExceptionHandlerWrapper(object):

    # Wrapper to be applied to all the view handler. Records the
    # time spent in the view handler as separate function node,
    # names the web transaction after the name of the view
    # handler and captures errors.

    def __init__(self, wrapped, priority):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped
        self.__priority = priority

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor, self.__priority)

    def __call__(self, request, resolver, exc_info):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            transaction.name_transaction(self.__name, priority=self.__priority)
            transaction.notice_error(exc_info[0], exc_info[1], exc_info[2])
            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name=self.__name):
                try:
                    return self.__wrapped(request, resolver, exc_info)
                except:
                    # Python 2.5 doesn't allow *args before keywords.
                    # See http://bugs.python.org/issue3473.
                    exc_info = sys.exc_info()
                    transaction.notice_error(exc_info[0], exc_info[1],
                                             exc_info[2])
                    raise
                finally:
                    exc_info = None
        else:
            return self.__wrapped(request, resolver, exc_info)

def instrument_django_core_handlers_wsgi(module):

    # Wrap the WSGI application entry point. If this is also
    # wrapped from the WSGI script file or by the WSGI hosting
    # mechanism then those will take precedence.

    newrelic.api.web_transaction.wrap_wsgi_application(
            module, 'WSGIHandler.__call__')

    # Attach a pre function to handle_uncaught_exception() of
    # WSGIHandler so that can capture exception details of any
    # exception which wasn't caught and dealt with by an
    # exception middleware. The handle_uncaught_exception()
    # function produces a 500 error response page and otherwise
    # suppresses the exception, so last chance to do this as
    # exception will not propogate up to the WSGI application.

    def uncaught_exception(handler, request, resolver, exc_info):

        # Record the exception details passed into the
        # function against the current transaction object.

        transaction = newrelic.api.transaction.transaction()
        if transaction:
            transaction.notice_error(*exc_info)

    #newrelic.api.name_transaction.wrap_name_transaction(
    #        module, 'WSGIHandler.handle_uncaught_exception',
    #        priority=1)

    #newrelic.api.pre_function.wrap_pre_function(
    #        module, 'WSGIHandler.handle_uncaught_exception',
    #        uncaught_exception)

    newrelic.api.object_wrapper.wrap_object(module,
            'WSGIHandler.handle_uncaught_exception',
            UncaughtExceptionHandlerWrapper, (1,))

class ViewHandlerWrapper(object):

    # Wrapper to be applied to all the view handler. Records the
    # time spent in the view handler as separate function node,
    # names the web transaction after the name of the view
    # handler and captures errors.

    def __init__(self, wrapped, priority):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped
        self.__priority = priority

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor, self.__priority)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            transaction.name_transaction(self.__name, priority=self.__priority)
            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name=self.__name):
                try:
                    return self.__wrapped(*args, **kwargs)
                except:
                    # Python 2.5 doesn't allow *args before keywords.
                    # See http://bugs.python.org/issue3473.
                    exc_info = sys.exc_info()
                    transaction.notice_error(exc_info[0], exc_info[1],
                            exc_info[2], ignore_errors=['django.http.Http404'])
                    raise
                finally:
                    exc_info = None
        else:
            return self.__wrapped(*args, **kwargs)

def wrap_view_handler(function):

    # Ensure we don't wrap the view handler more than once. This
    # looks like it may occur in cases where the resolver is
    # called recursively.

    if type(function) is not ViewHandlerWrapper:
        return ViewHandlerWrapper(function, priority=3)

    return function

class ResolverWrapper(object):

    # Wrapper to be applied to the URL resolver.  Captures a
    # Resolver404 exception and names the web transaction as a
    # generic 404 with group 'Uri'. This is to avoid problem of
    # metric explosion on URLs which didn't actually map to a
    # valid resource. If there is a 404 handler then this will
    # get overriden again later so this is just a default for
    # where no 404 handler. If resolver returns valid result
    # then wrap the view handler returned. The type of the
    # result changes across Django versions so need to check and
    # adapt as necessary.

    def __init__(self, wrapped):
        self.__wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            Resolver404 = sys.modules[
                    'django.core.urlresolvers'].Resolver404
            try:
                result = self.__wrapped(*args, **kwargs)
                if type(result) == type(()):
                    callback, callback_args, callback_kwargs = result
                    result = (wrap_view_handler(callback),
                            callback_args, callback_kwargs)
                else:
                    result.func = wrap_view_handler(result.func)
                return result
            except Resolver404:
                #transaction.name_transaction('404', group='Uri',
                #        priority=2)
                raise
        else:
            return self.__wrapped(*args, **kwargs)

class Resolver404Wrapper(object):

    # Wrapper to be applied to the URL resolver for 404 lookups.

    def __init__(self, wrapped):
        self.__wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            callback, param_dict = self.__wrapped(*args, **kwargs)
            return (wrap_view_handler(callback), param_dict)
        else:
            return self.__wrapped(*args, **kwargs)

def instrument_django_core_urlresolvers(module):

    # Wrap method which maps a string version of a function
    # name as used in urls.py pattern so can capture any
    # exception which is raised during that process.
    # Normally Django captures import errors at this point
    # and then reraises a ViewDoesNotExist exception with
    # details of the original error and traceback being
    # lost. We thus intercept it here so can capture that
    # traceback which is otherwise lost. Although we ignore
    # a Http404 exception here, it probably is never the
    # case that one can be raised by get_callable().

    newrelic.api.error_trace.wrap_error_trace(module,
            'get_callable', ignore_errors=['django.http.Http404'])

    # Wrap methods which resolves a request to a view handler.
    # This can be called against a resolver initialised against
    # a custom URL conf associated with a specific request, or a
    # resolver which uses the default URL conf.

    newrelic.api.object_wrapper.wrap_object(module,
            'RegexURLResolver.resolve', ResolverWrapper)

    newrelic.api.object_wrapper.wrap_object(module,
            'RegexURLResolver.resolve404', Resolver404Wrapper)

def instrument_django_template(module):

    # Wrap methods for rendering of Django templates. The name
    # of the method changed in between Django versions so need
    # to check for which one we have. The name of the function
    # trace node is taken from the name of the template. This
    # should be a relative path with the template loader
    # uniquely associating it with a specific template library.
    # Therefore do not need to worry about making it absolute as
    # meaning should be known in the context of the specific
    # Django site.

    def template_name(template, *args):
        return template.name

    if hasattr(module.Template, '_render'):
        newrelic.api.function_trace.wrap_function_trace(
                module, 'Template._render',
                name=template_name, group='Template/Render')
    else:
        newrelic.api.function_trace.wrap_function_trace(
                module, 'Template.render',
                name=template_name, group='Template/Render')

    # Register template tags used for manual insertion of RUM
    # header and footer.
    #
    # TODO This perhaps could be separated out into a Django
    # application and no longer added automaticaly. Instead
    # would be up to user to add a New Relic application into
    # INSTALLED_APPS to get access to the template tag library
    # for browser monitoring. Note that these don't have to be
    # installed for auto RUM to work.

    library = module.Library()
    library.simple_tag(newrelic_browser_timing_header)
    library.simple_tag(newrelic_browser_timing_footer)

    module.libraries['django.templatetags.newrelic'] = library

def instrument_django_template_loader_tags(module):

    # Wrap template block node for timing, naming the node after
    # the block name as defined in the template rather than
    # function name.

    class TemplateBlockWrapper(object):

        def __init__(self, wrapped):
            if type(wrapped) == types.TupleType:
                (instance, wrapped) = wrapped
            else:
                instance = None
            self.__instance = instance
            self.__wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.__wrapped, name)

        def __get__(self, instance, klass):
            if instance is None:
                return self
            descriptor = self.__wrapped.__get__(instance, klass)
            return self.__class__((instance, descriptor))

        def __call__(self, *args, **kwargs):
            transaction = newrelic.api.transaction.transaction()
            if transaction:
                with newrelic.api.function_trace.FunctionTrace(
                        transaction, name=self.__instance.name,
                        group='Template/Block'):
                    return self.__wrapped(*args, **kwargs)
            else:
                return self.__wrapped(*args, **kwargs)

    newrelic.api.object_wrapper.wrap_object(module,
            'BlockNode.render', TemplateBlockWrapper)

def instrument_django_core_servers_basehttp(module):

    # Allow 'runserver' to be used with Django <= 1.3. To do
    # this we wrap the WSGI application argument on the way in
    # so that the run() method gets the wrapped instance.
    #
    # Although this works, if anyone wants to use it and make
    # it reliable, they may need to first need to patch Django
    # as explained in the ticket:
    #
    #   https://code.djangoproject.com/ticket/16241
    #
    # as the Django 'runserver' is not WSGI compliant due to a
    # bug in its handling of errors when writing response.
    #
    # The way the agent now uses a weakref dictionary for the
    # transaction object may be enough to ensure the prior 
    # transaction is cleaned up properly when it is deleted,
    # but not absolutely sure that will always work. Thus is
    # still a risk of error on subsequent request saying that
    # there is an active transaction.
    #
    # TODO Later versions of Django use the wsgiref server
    # instead which will likely need to be dealt with via
    # instrumentation of the wsgiref module or some other means.

    def wrap_wsgi_application_entry_point(server, application, **kwargs):
      return ((server, newrelic.api.web_transaction.WSGIApplicationWrapper(
                application),), kwargs)

    # XXX Because of risk of people still trying to use the
    # inbuilt Django development server and since the code is
    # not going to be changed, could just patch it to fix
    # problem and the instrumentation we need.

    if hasattr(module.ServerHandler, 'run'):

        # Patch the server to make it work properly.

        def run(self, application):
            try:
                self.setup_environ()
                self.result = application(self.environ, self.start_response)
                self.finish_response()
            except:
                self.handle_error()
            finally:
                self.close()


        def close(self):
            if self.result is not None:
                try:
                    self.request_handler.log_request(
                            self.status.split(' ',1)[0], self.bytes_sent)
                finally:
                    try:
                        if hasattr(self.result,'close'):
                            self.result.close()
                    finally:
                        self.result = None
                        self.headers = None
                        self.status = None
                        self.environ = None
                        self.bytes_sent = 0
                        self.headers_sent = False

	# Leaving this out for now to see whether weakref solves
	# the problem.

        #module.ServerHandler.run = run
        #module.ServerHandler.close = close

        # Now wrap it with our instrumentation.

        newrelic.api.in_function.wrap_in_function(module,
                'ServerHandler.run', wrap_wsgi_application_entry_point)

def instrument_django_contrib_staticfiles_views(module):
    if type(module.serve) is not ViewHandlerWrapper:
        module.serve = ViewHandlerWrapper(module.serve, priority=3)

def instrument_django_contrib_staticfiles_handlers(module):
    newrelic.api.name_transaction.wrap_name_transaction(module,
        'StaticFilesHandler.serve')

def instrument_django_views_debug(module):
    module.technical_404_response = ViewHandlerWrapper(
            module.technical_404_response, priority=1)
    module.technical_500_response = ViewHandlerWrapper(
            module.technical_500_response, priority=1)

def instrument_django_http_multipartparser(module):
    newrelic.api.function_trace.wrap_function_trace(
            module, 'MultiPartParser.parse')
