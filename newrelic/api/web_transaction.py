import os
import sys
import types
import inspect
import urlparse
import cgi

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class WebTransaction(newrelic.api.transaction.Transaction):

    def __init__(self, application, environ):

	# The web transaction can be enabled/disabled by
	# the value of the variable "newrelic.enabled"
	# in the WSGI environ dictionary. We need to check
        # this before initialising the transaction as needs
        # to be passed in base class constructor. The
        # default is None, which would then result in the
        # base class making the decision based on whether
        # application or agent as a whole are enabled.

        enabled = self._environ_setting(
                environ, 'newrelic.enabled', None)

        # Initialise the common transaction base class.

        newrelic.api.transaction.Transaction.__init__(self,
                application, enabled)

	# Bail out if the transaction is running in a
	# disabled state.

        if not self.enabled:
            return

        # Check for override settings from WSGI environ.

        self.background_task = self._environ_setting(
                environ, 'newrelic.background_task', False)
        self.ignore = self._environ_setting(
                environ, 'newrelic.ignore', False)
        self.ignore_apdex = self._environ_setting(
                environ, 'newrelic.ignore_apdex', False)

	# Extract from the WSGI environ dictionary
	# details of the URL path. This will be set as
	# default path for the web transaction. This can
	# be overridden by framework to be more specific
	# to avoid metrics explosion problem resulting
	# from too many distinct URLs for same resource
	# due to use of REST style URL concepts or
	# otherwise.

        request_uri = environ.get('REQUEST_URI', None)
        script_name = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)

        self._request_uri = request_uri

        if script_name is not None or path_info is not None:
            if path_info is None:
                path = script_name
            elif script_name is None:
                path = path_info
            else:
                path = script_name + path_info

            self.name_transaction(path, 'Uri')

            if self._request_uri is None:
                self._request_uri = path
        else:
            if request_uri is not None:
                self.name_transaction(request_uri, 'Uri')

	# See if the WSGI environ dictionary includes
	# the special 'X-Queue-Start' HTTP header. This
	# header is an optional header that can be set
	# within the underlying web server or WSGI
	# server to indicate when the current request
	# was first received and ready to be processed.
	# The difference between this time and when
	# application starts processing the request is
	# the queue time and represents how long spent
	# in any explicit request queuing system, or how
	# long waiting in connecting state against
	# listener sockets where request needs to be
	# proxied between any processes within the
	# application server.
	#
	# Note that mod_wsgi 4.0 sets its own distinct
	# variable called mod_wsgi.queue_start so that
	# not necessary to enable and use mod_headers to
	# add X-Queue-Start. So also check for that, but
	# give priority to the explicitly added header
	# in case that header was added in front end
	# server to Apache instead although for that
	# case they should be using X-Request-Start
	# which do not support here yet as PHP agent
	# core doesn't have a way of tracking front end
	# web server time.

        value = environ.get('HTTP_X_QUEUE_START', None)

        if value and isinstance(value, basestring):
            if value.startswith('t='):
                try:
                    self._queue_start = int(value[2:])/1000000.0
                except:
                    pass

        # Capture query request string parameters.

        value = environ.get('QUERY_STRING', None)

        if value:
            try:
                params = urlparse.parse_qs(value)
            except:
                params = cgi.parse_qs(value)
            self.request_parameters.update(params)

    def _environ_setting(self, environ, name, default=False):
        flag = environ.get(name, default)
        if default is None or default:
            if isinstance(flag, basestring):
                flag = not flag.lower() in ['off', 'false', '0']
        else:
            if isinstance(flag, basestring):
                flag = flag.lower() in ['on', 'true', '1']
        return flag

    def browser_timing_header(self):
        return ''

    def browser_timing_footer(self):
        return ''

if _agent_mode not in ('julunggul',):
    import _newrelic
    WebTransaction = _newrelic.WebTransaction

class _WSGIApplicationIterable(object):
 
    def __init__(self, transaction, generator):
        self.transaction = transaction
        self.generator = generator
 
    def __iter__(self):
        for item in self.generator:
            yield item
 
    def close(self):
        try:
            if hasattr(self.generator, 'close'):
                self.generator.close()
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.transaction.__exit__(None, None, None)
 
class WSGIApplicationWrapper(object):

    def __init__(self, wrapped, application=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        if type(application) != newrelic.api.application.Application:
            application = newrelic.api.application.application(application)

        self._nr_application = application

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application)

    def __call__(self, environ, start_response):
        transaction = newrelic.api.transaction.transaction()

	# Check to see if we are being called within the
	# context of any sort of transaction. If we are,
	# then we don't bother doing anything and just
	# call the wrapped function.

        if transaction:
            return self._nr_next_object(environ, start_response)

        # Otherwise treat it as top level transaction.
 
        transaction = WebTransaction(self._nr_application, environ)
        transaction.__enter__()
 
        def _start_response(status, response_headers, *args):
            transaction.response_code = int(status.split(' ')[0])
            return start_response(status, response_headers, *args)
 
        try:
            result = self._nr_next_object(environ, _start_response)
        except:
            transaction.__exit__(*sys.exc_info())
            raise
 
        return _WSGIApplicationIterable(transaction, result)

def wsgi_application(application=None):
    def decorator(wrapped):
        return WSGIApplicationWrapper(wrapped, application)
    return decorator

def wrap_wsgi_application(module, object_path, application=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            WSGIApplicationWrapper, (application, ))

if _agent_mode not in ('ungud', 'julunggul'):
    import _newrelic
    wsgi_application = _newrelic.wsgi_application
    wrap_wsgi_application = _newrelic.wrap_wsgi_application
    WSGIApplicationWrapper = _newrelic.WSGIApplicationWrapper
