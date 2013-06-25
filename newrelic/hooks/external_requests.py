from newrelic.agent import (ExternalTrace, ObjectWrapper, current_transaction)


def request_send_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    parent = transaction._parent_node()

    if not parent or parent.terminal_node():
        return wrapped(*args, **kwargs)

    def _args(request, *args, **kwargs):
        return request

    # Check if the instance variable has an attr called 'request'. If it is
    # present then instance is of type Session, so we need to extract the first
    # arg which has the prepared_request obj and wrap it. If not then the
    # instance var is of type Request and we can directly wrap it.
    #
    # The 'instance' var will be of type 'Session' for Requests v1.0 and above
    # and it'll be of type 'Request' for versions older than 1.0.

    if hasattr(instance, 'request'):
        request = _args(*args, **kwargs)
    else:
        request = instance

    with ExternalTrace(transaction, library='requests', url=request.url) \
            as tracer:
        try:
            # Add our own extra headers to outgoing request.

            outgoing_headers = ExternalTrace.generate_request_headers(transaction)

            # Requests v0.5.0 sets headers to None if there are no additional
            # headers.

            if request.headers is None:
                request.headers = dict(outgoing_headers)
            else:
                request.headers.update(outgoing_headers)

            response = wrapped(*args, **kwargs)
        except:  # Catch all
            raise
        else:

            # Older versions of requests module would return a bool instead of
            # response obj.

            if hasattr(response, 'headers'):
                headers = response.headers
            else:
                headers = request.response.headers

            # Parse the headers from the response object and extract the NR
            # specific headers.

            tracer.process_response_headers(headers.items())

        return response

def instrument_requests_models(module):

    # Request version 1.0.0 and above has the send() method on the
    # session.Session class instead of the models.Request class. Checking to
    # see if we need to wrap the models.Request.

    if hasattr(module.Request, 'send'):
        module.Request.send = ObjectWrapper(module.Request.send, None,
                                    request_send_wrapper)

def instrument_requests_sessions(module):

    # Request version 1.0.0 and above has the send() method on the
    # session.Session class instead of the models.Request class. Checking to
    # see if we need to wrap the session.Session.

    if hasattr(module.Session, 'send'):
        module.Session.send = ObjectWrapper(module.Session.send, None,
                                            request_send_wrapper)

