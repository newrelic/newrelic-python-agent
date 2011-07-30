import os
import sys
import types
import inspect

import _newrelic

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

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

	# Check to see if we are being called within the context
	# of any sort of transaction. If we are, then we don't bother
        # doing anything and just call the wrapped function.

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

if not _agent_mode in ('ungud', 'julunggul'):
    wsgi_application = _newrelic.wsgi_application
    wrap_wsgi_application = _newrelic.wrap_wsgi_application
    WSGIApplicationWrapper = _newrelic.WSGIApplicationWrapper
