import functools

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        ExternalTrace)
import newrelic.api.external_trace

def _nr_wrapper_httplib2_connect_wrapper(scheme):

    def _nr_wrapper_httplib2_connect_wrapper_inner(wrapped, instance, args,
            kwargs):
      transaction = current_transaction()

      if transaction is None:
          return wrapped(*args, **kwargs)

      def _connect_unbound(instance, *args, **kwargs):
          return instance

      if instance is None:
          instance = _connect_unbound(*args, **kwargs)

      connection = instance

      url = '%s://%s' % (scheme, connection.host)

      with ExternalTrace(transaction, library='httplib2', url=url) as tracer:
          # Add the tracer to the connection object. The tracer will be
          # used in getresponse() to add back into the external trace,
          # after the trace has already completed, details from the
          # response headers.

          connection._nr_external_tracer = tracer

          return wrapped(*args, **kwargs)

    return _nr_wrapper_httplib2_connect_wrapper_inner

def instrument(module):

    wrap_function_wrapper(module, 'HTTPConnectionWithTimeout.connect',
            _nr_wrapper_httplib2_connect_wrapper('http'))

    wrap_function_wrapper(module, 'HTTPSConnectionWithTimeout.connect',
            _nr_wrapper_httplib2_connect_wrapper('https'))

    def url_request(connection, uri, *args, **kwargs):
        return uri

    newrelic.api.external_trace.wrap_external_trace(
           module, 'Http.request', 'httplib2', url_request)
