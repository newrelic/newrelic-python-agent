import os
import sys
import types
import inspect

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

	# Extract from the WSGI environ dictionary
	# details of the URL path. This will be set as
	# default path for the web transaction. This can
	# be overridden by framework to be more specific
	# to avoid metrics explosion problem resulting
	# from too many distinct URLs for same resource
	# due to use of REST style URL concepts or
	# otherwise.

        script_name = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)

        if script_name is not None or path_info is not None:
            if path_info is None:
                path = script_name
            elif script_name is None:
                path = path_info
            else:
                path = script_name + path_info

            self._path = path
            self._path_type = newrelic.api.transaction.PATH_TYPE_URI

        else:
            request_uri = environ.get('REQUEST_URI', None)

            if request_uri is not None:
                self._path = request_uri

        # Check for override settings from WSGI environ.

        self.background_task = self._environ_setting(
                environ, 'newrelic.background_task', False)
        self.ignore = self._environ_setting(
                environ, 'newrelic.ignore', False)
        self.ignore_apdex = self._environ_setting(
                environ, 'newrelic.ignore_apdex', False)

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
