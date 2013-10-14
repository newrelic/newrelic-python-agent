import sys
import threading
import types

import newrelic.packages.six as six

from newrelic.api.error_trace import wrap_error_trace
from newrelic.api.function_trace import (FunctionTrace, wrap_function_trace)
from newrelic.api.in_function import wrap_in_function
from newrelic.api.object_wrapper import (ObjectWrapper, callable_name)
from newrelic.api.transaction_name import wrap_transaction_name
from newrelic.api.post_function import wrap_post_function
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WSGIApplicationWrapper

# Response middleware for automatically inserting RUM header and
# footer into HTML response returned by application

def browser_timing_middleware(request, response):

    # Don't do anything if receive a streaming response which
    # was introduced in Django 1.5. Need to avoid this as there
    # will be no 'content' attribute. Alternatively there may be
    # a 'content' attribute which flattens the stream, which if
    # we access, will break the streaming and/or buffer what is
    # potentially a very large response in memory contrary to
    # what user wanted by explicitly using a streaming response
    # object in the first place. To preserve streaming but still
    # do RUM insertion, need to move to a WSGI middleware and
    # deal with how to update the content length.

    if hasattr(response, 'streaming_content'):
        return response

    # Need to be running within a valid web transaction.

    transaction = current_transaction()

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

    if ctype != 'text/html' and not ctype.startswith('text/html;'):
        return response

    # Don't risk it if content encoding already set.

    if response.has_header('Content-Encoding'):
        return response

    # No point continuing if header is empty. This can occur if
    # RUM is not enabled within the UI. It is assumed at this
    # point that if header is not empty, then footer will be not
    # empty. We don't want to generate the footer just yet as
    # want to do that as late as possible so that application
    # server time in footer is as accurate as possible. In
    # particular, if the response content is generated on demand
    # then the flattening of the response could take some time
    # and we want to track that. We thus generate footer below
    # at point of insertion.

    header = transaction.browser_timing_header()

    if not header:
        return response

    header = six.b(header)

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

    start = content.find(b'<head')
    end = content.rfind(b'</body>', -1024)
    if start != -1 and end != -1:
        offset = content.find(b'</head>', start)
        if content.find(b'X-UA-Compatible', start, offset) == -1:
            start = content.find(b'>', start, start+1024)
        elif offset != -1:
            start = offset - 1
        if start != -1 and start < end:
            parts = []
            parts.append(content[0:start+1])
            parts.append(header)
            parts.append(content[start+1:end])

            footer = transaction.browser_timing_footer()
            footer = six.b(footer)

            parts.append(footer)
            parts.append(content[end:])
            response.content = b''
            content = b''.join(parts)
            response.content = content
    elif start == -1 and end != -1:
        start = content.find(b'<body')
        if start != -1 and start < end:
            parts = []
            parts.append(content[0:start])
            parts.append(b'<head>')
            parts.append(header)
            parts.append(b'</head>')
            parts.append(content[start:end])

            footer = transaction.browser_timing_footer()
            footer = six.b(footer)

            parts.append(footer)
            parts.append(content[end:])
            response.content = ''
            content = b''.join(parts)
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
        name = callable_name(function)
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
    transaction = current_transaction()
    return transaction and transaction.browser_timing_header() or ''

def newrelic_browser_timing_footer():
    transaction = current_transaction()
    return transaction and transaction.browser_timing_footer() or ''

# Addition of instrumentation for middleware. Can only do this
# after Django itself has constructed the list of middleware. We
# also insert the RUM middleware into the response middleware.

middleware_instrumentation_lock = threading.Lock()

def wrap_leading_middleware(middleware):

    # Wrapper to be applied to middleware executed prior to the
    # view handler being executed. Records the time spent in the
    # middleware as separate function node and also attempts to
    # name the web transaction after the name of the middleware
    # with success being determined by the priority.

    def wrapper(wrapped):
        # The middleware if a class method would already be
        # bound at this point, so is safe to determine the name
        # when it is being wrapped rather than on each
        # invocation.

        name = callable_name(wrapped)

        def wrapper(wrapped, instance, args, kwargs):
            transaction = current_transaction()

            if transaction is None:
                return wrapped(*args, **kwargs)

            before = (transaction.name, transaction.group)

            with FunctionTrace(transaction, name=name):
                try:
                    return wrapped(*args, **kwargs)

                finally:
                    # We want to name the transaction after this
                    # middleware but only if the transaction wasn't
                    # named from within the middleware itself explicity.

                    after = (transaction.name, transaction.group)
                    if before == after:
                        transaction.set_transaction_name(name, priority=2)

        return ObjectWrapper(wrapped, None, wrapper)

    for wrapped in middleware:
        yield wrapper(wrapped)

def wrap_view_middleware(middleware):

    # XXX This is no longer being used. The changes to strip the
    # wrapper from the view handler when passed into the function
    # urlresolvers.reverse() solves most of the problems. To back
    # that up, the object wrapper now proxies various special
    # methods so that comparisons like '==' will work. The object
    # wrapper can even be used as a standin for the wrapped object
    # when used as a key in a dictionary and will correctly match
    # the original wrapped object.

    # Wrapper to be applied to view middleware. Records the time
    # spent in the middleware as separate function node and also
    # attempts to name the web transaction after the name of the
    # middleware with success being determined by the priority.
    # This wrapper is special in that it must strip the wrapper
    # from the view handler when being passed to the view
    # middleware to avoid issues where middleware wants to do
    # comparisons between the passed middleware and some other
    # value. It is believed that the view handler should never
    # actually be called from the view middleware so not an
    # issue that no longer wrapped at this point.

    def wrapper(wrapped):
        # The middleware if a class method would already be
        # bound at this point, so is safe to determine the name
        # when it is being wrapped rather than on each
        # invocation.

        name = callable_name(wrapped)

        def wrapper(wrapped, instance, args, kwargs):
            transaction = current_transaction()

            def _wrapped(request, view_func, view_args, view_kwargs):
                # This strips the view handler wrapper before call.

                if hasattr(view_func, '_nr_last_object'):
                    view_func = view_func._nr_last_object

                return wrapped(request, view_func, view_args, view_kwargs)

            if transaction is None:
                return _wrapped(*args, **kwargs)

            before = (transaction.name, transaction.group)

            with FunctionTrace(transaction, name=name):
                try:
                    return _wrapped(*args, **kwargs)

                finally:
                    # We want to name the transaction after this
                    # middleware but only if the transaction wasn't
                    # named from within the middleware itself explicity.

                    after = (transaction.name, transaction.group)
                    if before == after:
                        transaction.set_transaction_name(name, priority=2)

        return ObjectWrapper(wrapped, None, wrapper)

    for wrapped in middleware:
        yield wrapper(wrapped)

def wrap_trailing_middleware(middleware):

    # Wrapper to be applied to trailing middleware executed
    # after the view handler. Records the time spent in the
    # middleware as separate function node. Transaction is never
    # named after these middleware.

    def wrapper(wrapped):
        # The middleware if a class method would already be
        # bound at this point, so is safe to determine the name
        # when it is being wrapped rather than on each
        # invocation.

        name = callable_name(wrapped)

        def wrapper(wrapped, instance, args, kwargs):
            transaction = current_transaction()

            if transaction is None:
                return wrapped(*args, **kwargs)

            with FunctionTrace(transaction, name=name):
                return wrapped(*args, **kwargs)

        return ObjectWrapper(wrapped, None, wrapper)

    for wrapped in middleware:
        yield wrapper(wrapped)

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
            handler._request_middleware = list(
                    wrap_leading_middleware(
                    handler._request_middleware))

        if hasattr(handler, '_view_middleware'):
            handler._view_middleware = list(
                    wrap_leading_middleware(
                    handler._view_middleware))

        if hasattr(handler, '_template_response_middleware'):
            handler._template_response_middleware = list(
                  wrap_trailing_middleware(
                  handler._template_response_middleware))

        if hasattr(handler, '_response_middleware'):
            handler._response_middleware = list(
                    wrap_trailing_middleware(
                    handler._response_middleware))

        if hasattr(handler, '_exception_middleware'):
            handler._exception_middleware = list(
                    wrap_trailing_middleware(
                    handler._exception_middleware))

    finally:
        lock.release()

# Post import hooks for modules.

def instrument_django_core_handlers_base(module):

    # Attach a post function to load_middleware() method of
    # BaseHandler to trigger insertion of browser timing
    # middleware and wrapping of middleware for timing etc.

    wrap_post_function(module, 'BaseHandler.load_middleware',
            insert_and_wrap_middleware)

def wrap_handle_uncaught_exception(middleware):

    # Wrapper to be applied to handler called when exceptions
    # propagate up to top level from middleware. Records the
    # time spent in the handler as separate function node. Names
    # the web transaction after the name of the handler if not
    # already named at higher priority and capture further
    # errors in the handler.

    name = callable_name(middleware)

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        def _wrapped(request, resolver, exc_info):
            transaction.set_transaction_name(name, priority=1)
            transaction.record_exception(*exc_info)

            try:
                return wrapped(request, resolver, exc_info)

            except:  # Catch all
                transaction.record_exception(*sys.exc_info())
                raise

        with FunctionTrace(transaction, name=name):
            return _wrapped(*args, **kwargs)

    return ObjectWrapper(middleware, None, wrapper)

def instrument_django_core_handlers_wsgi(module):

    # Wrap the WSGI application entry point. If this is also
    # wrapped from the WSGI script file or by the WSGI hosting
    # mechanism then those will take precedence.

    import django

    framework = ('Django', django.get_version())

    module.WSGIHandler.__call__ = WSGIApplicationWrapper(
          module.WSGIHandler.__call__, framework=framework)

    # Wrap handle_uncaught_exception() of WSGIHandler so that
    # can capture exception details of any exception which
    # wasn't caught and dealt with by an exception middleware.
    # The handle_uncaught_exception() function produces a 500
    # error response page and otherwise suppresses the
    # exception, so last chance to do this as exception will not
    # propogate up to the WSGI application.

    module.WSGIHandler.handle_uncaught_exception = (
            wrap_handle_uncaught_exception(
            module.WSGIHandler.handle_uncaught_exception))

def wrap_view_handler(wrapped, priority=3):

    # Ensure we don't wrap the view handler more than once. This
    # looks like it may occur in cases where the resolver is
    # called recursively. We flag that view handler was wrapped
    # using the '_nr_django_view_handler' attribute.

    if hasattr(wrapped, '_nr_django_view_handler'):
        return wrapped

    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        transaction.set_transaction_name(name, priority=priority)

        with FunctionTrace(transaction, name=name):
            try:
                return wrapped(*args, **kwargs)

            except:  # Catch all
                # Python 2.5 doesn't allow *args before keywords.
                # See http://bugs.python.org/issue3473.
                exc_info = sys.exc_info()
                transaction.record_exception(exc_info[0], exc_info[1],
                        exc_info[2], ignore_errors=['django.http:Http404',
                        'django.http.response:Http404'])
                raise

            finally:
                exc_info = None

    result = ObjectWrapper(wrapped, None, wrapper)
    result._nr_django_view_handler = True

    return result

def wrap_url_resolver(wrapped):

    # Wrap URL resolver. If resolver returns valid result then
    # wrap the view handler returned. The type of the result
    # changes across Django versions so need to check and adapt
    # as necessary. For a 404 then a user supplied 404 handler
    # or the default 404 handler should get later invoked and
    # transaction should be named after that.

    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if hasattr(transaction, '_nr_django_url_resolver'):
            return wrapped(*args, **kwargs)

        # Tag the transaction so we know when we are in the top
        # level call to the URL resolver as don't want to show
        # the inner ones as would be one for each url pattern.

        transaction._nr_django_url_resolver = True

        def _wrapped(path):
            # XXX This can raise a Resolver404. If this is not dealt
            # with, is this the source of our unnamed 404 requests.

            with FunctionTrace(transaction, name=name, label=path):
                result = wrapped(path)

                if type(result) == type(()):
                    callback, callback_args, callback_kwargs = result
                    result = (wrap_view_handler(callback, priority=3),
                            callback_args, callback_kwargs)
                else:
                    result.func = wrap_view_handler(result.func, priority=3)

                return result

        try:
            return _wrapped(*args, **kwargs)

        finally:
            del transaction._nr_django_url_resolver

    return ObjectWrapper(wrapped, None, wrapper)

def wrap_url_resolver_nnn(wrapped, priority=1):

    # Wrapper to be applied to the URL resolver for errors.

    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with FunctionTrace(transaction, name=name):
            callback, param_dict = wrapped(*args, **kwargs)
            return (wrap_view_handler(callback, priority=priority),
                    param_dict)

    return ObjectWrapper(wrapped, None, wrapper)

def wrap_url_reverse(wrapped):

    # Wrap the URL resolver reverse lookup. Where the view
    # handler is passed in we need to strip any instrumentation
    # wrapper to ensure that it doesn't interfere with the
    # lookup process. Technically this may now not be required
    # as we have improved the proxying in the object wrapper,
    # but do it just to avoid any potential for problems.

    def wrapper(wrapped, instance, args, kwargs):
        def execute(viewname, *args, **kwargs):
            if hasattr(viewname, '_nr_last_object'):
                viewname = viewname._nr_last_object
            return wrapped(viewname, *args, **kwargs)
        return execute(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

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

    wrap_error_trace(module, 'get_callable', ignore_errors=[
            'django.http:Http404', 'django.http.response:Http404'])

    # Wrap methods which resolves a request to a view handler.
    # This can be called against a resolver initialised against
    # a custom URL conf associated with a specific request, or a
    # resolver which uses the default URL conf.

    module.RegexURLResolver.resolve = wrap_url_resolver(
            module.RegexURLResolver.resolve)

    # Wrap methods which resolve error handlers. For 403 and 404
    # we give these higher naming priority over any prior
    # middleware or view handler to give them visibility. For a
    # 500, which will be triggered for unhandled exception, we
    # leave any original name derived from a middleware or view
    # handler in place so error details identify the correct
    # transaction.

    if hasattr(module.RegexURLResolver, 'resolve403'):
        module.RegexURLResolver.resolve403 = wrap_url_resolver_nnn(
                module.RegexURLResolver.resolve403, priority=3)

    module.RegexURLResolver.resolve404 = wrap_url_resolver_nnn(
            module.RegexURLResolver.resolve404, priority=3)

    module.RegexURLResolver.resolve500 = wrap_url_resolver_nnn(
            module.RegexURLResolver.resolve500, priority=1)

    # Wrap function for performing reverse URL lookup to strip any
    # instrumentation wrapper when view handler is passed in.

    module.reverse = wrap_url_reverse(module.reverse)

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
        wrap_function_trace(module, 'Template._render',
                name=template_name, group='Template/Render')
    else:
        wrap_function_trace(module, 'Template.render',
                name=template_name, group='Template/Render')

    # Register template tags used for manual insertion of RUM
    # header and footer.
    #
    # TODO This can now be installed as a separate tag library
    # so should possibly look at deprecating this automatic
    # way of doing things.

    library = module.Library()
    library.simple_tag(newrelic_browser_timing_header)
    library.simple_tag(newrelic_browser_timing_footer)

    module.libraries['django.templatetags.newrelic'] = library

def wrap_template_block(wrapped):

    name = callable_name(wrapped)

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with FunctionTrace(transaction, name=instance.name,
                group='Template/Block'):
            return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

def instrument_django_template_loader_tags(module):

    # Wrap template block node for timing, naming the node after
    # the block name as defined in the template rather than
    # function name.

    module.BlockNode.render = wrap_template_block(module.BlockNode.render)

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

    import django

    framework = ('Django', django.get_version())

    def wrap_wsgi_application_entry_point(server, application, **kwargs):
      return ((server, WSGIApplicationWrapper(application,
              framework='Django'),), kwargs)

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
            except Exception:
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

        wrap_in_function(module, 'ServerHandler.run',
                wrap_wsgi_application_entry_point)

def instrument_django_contrib_staticfiles_views(module):
    if not hasattr(module.serve, '_nr_django_view_handler'):
        module.serve = wrap_view_handler(module.serve, priority=3)

def instrument_django_contrib_staticfiles_handlers(module):
    wrap_transaction_name(module, 'StaticFilesHandler.serve')

def instrument_django_views_debug(module):

    # Wrap methods for handling errors when Django debug
    # enabled. For 404 we give this higher naming priority over
    # any prior middleware or view handler to give them
    # visibility. For a 500, which will be triggered for
    # unhandled exception, we leave any original name derived
    # from a middleware or view handler in place so error
    # details identify the correct transaction.

    module.technical_404_response = wrap_view_handler(
            module.technical_404_response, priority=3)
    module.technical_500_response = wrap_view_handler(
            module.technical_500_response, priority=1)

def wrap_view_dispatch(wrapped):

    # Wrapper to be applied to dispatcher for class based views.

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        def _args(request, *args, **kwargs):
            return request

        view = instance
        request = _args(*args, **kwargs)

        # We can't intercept the delegated view handler when it
        # is looked up by the dispatch() method so we need to
        # duplicate the lookup mechanism.

        if request.method.lower() in view.http_method_names:
            handler = getattr(view, request.method.lower(),
                    view.http_method_not_allowed)
        else:
            handler = view.http_method_not_allowed

        name = callable_name(handler)
        transaction.set_transaction_name(name)

        with FunctionTrace(transaction, name=name):
            return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

def instrument_django_views_generic_base(module):
    module.View.dispatch = wrap_view_dispatch(module.View.dispatch)

def instrument_django_http_multipartparser(module):
    wrap_function_trace(module, 'MultiPartParser.parse')

def instrument_django_core_mail(module):
    wrap_function_trace(module, 'mail_admins')
    wrap_function_trace(module, 'mail_managers')
    wrap_function_trace(module, 'send_mail')

def instrument_django_core_mail_message(module):
    wrap_function_trace(module, 'EmailMessage.send')
