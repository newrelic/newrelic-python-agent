import sys

from newrelic.agent import (wrap_function_wrapper, current_transaction,
    FunctionTrace, callable_name)

from . import (retrieve_request_transaction, initiate_request_monitoring,
    suspend_request_monitoring, finalize_request_monitoring)

def wsgi_container_call_wrapper(wrapped, instance, args, kwargs):
    def _args(request, *args, **kwargs):
        return request

    # We need to check to see if an existing transaction object has
    # already been created for the request

    request = _args(*args, **kwargs)

    transaction = retrieve_request_transaction(request)

    # If there is no prior transaction we will need to create one.

    if not transaction:
        # Create the transaction but if it is None then it means
        # recording of transactions is not enabled and so need to
        # call the wrapped function immediately and return.

        transaction = initiate_request_monitoring(request)

        if transaction is None:
            return wrapped(*args, **kwargs)

        try:
            result = wrapped(*args, **kwargs)

        except:  # Catch all
            finalize_request_monitoring(request, *sys.exc_info())
            raise

        if not request.connection.stream.writing():
            finalize_request_monitoring(request)

        else:
            suspend_request_monitoring(request, name='Request/Output')

    else:
        # XXX Name the transaction after the URI. This is a
        # temporary fiddle to preserve old default URL naming
        # convention for WSGI applications until we move away
        # from that as a default.

        if transaction._request_uri is not None:
             transaction.set_transaction_name(
                     transaction._request_uri, 'Uri', priority=1)

        result = wrapped(*args, **kwargs)

    return result

class _WSGIApplicationIterable(object): 

    def __init__(self, transaction, generator): 
        self.transaction = transaction 
        self.generator = generator 

    def __iter__(self): 
        try: 
            with FunctionTrace(self.transaction, name='Response', 
                    group='Python/WSGI'): 
                for item in self.generator: 
                    yield item 

        except GeneratorExit: 
            raise 

        except: # Catch all 
            self.transaction.record_exception() 
            raise 

    def close(self): 
        try: 
            with FunctionTrace(self.transaction, name='Finalize', 
                    group='Python/WSGI'): 
                if hasattr(self.generator, 'close'): 
                    name = callable_name(self.generator.close) 
                    with FunctionTrace(self.transaction, name): 
                        self.generator.close() 

        except: # Catch all 
            self.transaction.record_exception() 

class _WSGIApplication(object): 

    def __init__(self, wsgi_application): 
        self.wsgi_application = wsgi_application 

    def __call__(self, environ, start_response): 
        transaction = current_transaction() 

        if transaction is None: 
            return self.wsgi_application(environ, start_response) 

        name = callable_name(self.wsgi_application) 

        with FunctionTrace(transaction, name='Application', 
                group='Python/WSGI'): 
            with FunctionTrace(transaction, name=name): 
                result = self.wsgi_application(environ, start_response) 

        return _WSGIApplicationIterable(transaction, result)

def wsgi_container_init_wrapper(wrapped, instance, args, kwargs):
    def _args(wsgi_application, *args, **kwargs):
        return wsgi_application

    wsgi_application = _args(*args, **kwargs)

    return wrapped(_WSGIApplication(wsgi_application))

def instrument_tornado_wsgi(module):
    wrap_function_wrapper(module, 'WSGIContainer.__init__',
            wsgi_container_init_wrapper)
    wrap_function_wrapper(module, 'WSGIContainer.__call__',
            wsgi_container_call_wrapper)
